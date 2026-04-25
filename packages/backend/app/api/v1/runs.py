from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import authenticate_user_token, get_current_user
from app.core.config import get_settings
from app.core.redis_client import get_sync_redis
from app.db.models.chat_session import ChatSession
from app.db.models.run import Run
from app.db.models.run_step import RunStep
from app.db.models.user import User
from app.db.session import get_db, get_session_factory
from app.services.memory import append_user_message
from app.services.run_scheduler import submit_run, submit_run_blocking

router = APIRouter()


class RunCreateRequest(BaseModel):
    mode: Literal["chat", "agent"]
    message: str = Field(min_length=1, max_length=32000)
    session_id: UUID | None = None
    model: str | None = None
    skill_allowlist: list[str] = Field(default_factory=lambda: ["*"])
    tools_enabled: bool | None = None
    await_completion: bool = False


class RunCreatedResponse(BaseModel):
    run_id: UUID
    session_id: UUID
    status: str


class RunStepResponse(BaseModel):
    id: UUID
    seq: int
    step_type: str
    name: str
    status: str
    detail: dict[str, Any] | None
    error: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class RunDetailResponse(BaseModel):
    id: UUID
    session_id: UUID
    mode: str
    status: str
    model: str
    error: str | None
    prompt_tokens: int
    completion_tokens: int
    summary: dict[str, Any] | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class RunListItem(BaseModel):
    id: UUID
    session_id: UUID
    mode: str
    status: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/runs", response_model=list[RunListItem])
def list_runs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Run]:
    rows = db.scalars(
        select(Run)
        .where(Run.user_id == user.id)
        .order_by(Run.created_at.desc())
        .limit(limit)
    ).all()
    return list(rows)


@router.post("/runs", response_model=RunCreatedResponse)
def create_run(
    body: RunCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RunCreatedResponse:
    settings = get_settings()

    if body.session_id is None:
        session = ChatSession(user_id=user.id, title=None)
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id
    else:
        session = db.get(ChatSession, body.session_id)
        if session is None or session.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        session_id = session.id

    r = get_sync_redis()
    append_user_message(db=db, r=r, session_id=session_id, content=body.message)

    model = body.model or settings.default_llm_model
    max_llm_calls = (
        settings.agent_max_steps if body.mode == "agent" else settings.chat_max_tool_rounds
    )
    tools_enabled = True if body.tools_enabled is None else bool(body.tools_enabled)

    run = Run(
        user_id=user.id,
        session_id=session_id,
        mode=body.mode,
        status="pending",
        model=model,
        summary={
            "skill_allowlist": body.skill_allowlist,
            "max_llm_calls": max_llm_calls,
            "tools_enabled": tools_enabled,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if body.await_completion:
        try:
            submit_run_blocking(run.id, timeout_s=300.0)
        except TimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(exc),
            ) from exc
    else:
        submit_run(run.id)

    db.refresh(run)
    return RunCreatedResponse(run_id=run.id, session_id=session_id, status=run.status)


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Run:
    run = db.get(Run, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/runs/{run_id}/trace", response_model=list[RunStepResponse])
def get_run_trace(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RunStep]:
    run = db.get(Run, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    steps = db.scalars(
        select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.seq.asc())
    ).all()
    return list(steps)


@router.websocket("/runs/{run_id}/stream")
async def stream_run(
    websocket: WebSocket,
    run_id: UUID,
    access_token: str | None = Query(default=None),
) -> None:
    if not access_token:
        await websocket.close(code=1008, reason="missing access_token")
        return

    factory = get_session_factory()
    db = factory()
    try:
        user = authenticate_user_token(db, token=access_token)
        run = db.get(Run, run_id) if user is not None else None
        if user is None or run is None or run.user_id != user.id:
            await websocket.close(code=1008, reason="unauthorized")
            return
    finally:
        db.close()

    await websocket.accept()

    r = get_sync_redis()
    key = f"run:{run_id}:events"
    offset = 0
    idle_ticks = 0

    while True:
        chunk = await asyncio.to_thread(r.lrange, key, 0, -1)
        if len(chunk) > offset:
            for raw in chunk[offset:]:
                await websocket.send_text(raw)
            offset = len(chunk)
            idle_ticks = 0
            try:
                last = json.loads(chunk[-1])
            except json.JSONDecodeError:
                last = {}
            if last.get("type") in ("run.completed", "error"):
                break
        else:
            idle_ticks += 1
            if idle_ticks > 600:
                await websocket.send_json({"type": "error", "message": "stream_idle_timeout"})
                break

        await asyncio.sleep(0.2)
