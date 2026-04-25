from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import authenticate_user_token, get_current_user
from app.core.redis_client import get_sync_redis
from app.db.models.user import User
from app.db.models.workflow import Workflow
from app.db.models.workflow_run import WorkflowRun
from app.db.models.workflow_run_step import WorkflowRunStep
from app.db.session import get_db, get_session_factory
from app.services.run_scheduler import submit_workflow_run, submit_workflow_run_blocking

router = APIRouter()


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    definition: dict[str, Any]


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    definition: dict[str, Any] | None = None


class WorkflowOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunCreate(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    await_completion: bool = False


class WorkflowRunOut(BaseModel):
    id: UUID
    workflow_id: UUID
    status: str
    inputs: dict[str, Any]
    outputs: dict[str, Any] | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowRunStepOut(BaseModel):
    id: UUID
    seq: int
    node_id: str
    step_type: str
    name: str
    status: str
    detail: dict[str, Any] | None
    error: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


@router.post("/workflows", response_model=WorkflowOut)
def create_workflow(
    body: WorkflowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    wf = Workflow(
        user_id=user.id,
        name=body.name,
        description=body.description,
        definition=body.definition,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("/workflows", response_model=list[WorkflowOut])
def list_workflows(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Workflow]:
    rows = db.scalars(
        select(Workflow).where(Workflow.user_id == user.id).order_by(Workflow.updated_at.desc())
    ).all()
    return list(rows)


@router.get("/workflows/{workflow_id}", response_model=WorkflowOut)
def get_workflow(
    workflow_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    wf = db.get(Workflow, workflow_id)
    if wf is None or wf.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return wf


@router.put("/workflows/{workflow_id}", response_model=WorkflowOut)
def update_workflow(
    workflow_id: UUID,
    body: WorkflowUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Workflow:
    wf = db.get(Workflow, workflow_id)
    if wf is None or wf.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    if body.name is not None:
        wf.name = body.name
    if body.description is not None:
        wf.description = body.description
    if body.definition is not None:
        wf.definition = body.definition
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.post("/workflows/{workflow_id}/runs", response_model=WorkflowRunOut)
def create_workflow_run(
    workflow_id: UUID,
    body: WorkflowRunCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkflowRun:
    wf = db.get(Workflow, workflow_id)
    if wf is None or wf.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    run = WorkflowRun(
        workflow_id=wf.id,
        user_id=user.id,
        status="pending",
        inputs=body.inputs,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if body.await_completion:
        try:
            submit_workflow_run_blocking(run.id, timeout_s=300.0)
        except TimeoutError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=str(exc),
            ) from exc
    else:
        submit_workflow_run(run.id)

    db.refresh(run)
    return run


@router.get("/workflow-runs", response_model=list[WorkflowRunOut])
def list_workflow_runs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[WorkflowRun]:
    rows = db.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.user_id == user.id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(limit)
    ).all()
    return list(rows)


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRunOut)
def get_workflow_run(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WorkflowRun:
    run = db.get(WorkflowRun, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


@router.get("/workflow-runs/{run_id}/trace", response_model=list[WorkflowRunStepOut])
def get_workflow_run_trace(
    run_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[WorkflowRunStep]:
    run = db.get(WorkflowRun, run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    steps = db.scalars(
        select(WorkflowRunStep)
        .where(WorkflowRunStep.workflow_run_id == run_id)
        .order_by(WorkflowRunStep.seq.asc())
    ).all()
    return list(steps)


@router.websocket("/workflow-runs/{run_id}/stream")
async def stream_workflow_run(
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
        run = db.get(WorkflowRun, run_id) if user is not None else None
        if user is None or run is None or run.user_id != user.id:
            await websocket.close(code=1008, reason="unauthorized")
            return
    finally:
        db.close()

    await websocket.accept()

    r = get_sync_redis()
    key = f"wf_run:{run_id}:events"
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
            if last.get("type") in ("workflow.completed", "error"):
                break
        else:
            idle_ticks += 1
            if idle_ticks > 600:
                await websocket.send_json({"type": "error", "message": "stream_idle_timeout"})
                break

        await asyncio.sleep(0.2)
