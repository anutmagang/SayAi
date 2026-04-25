from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.chat_message import ChatMessage


def _redis_key(session_id: UUID) -> str:
    return f"sess:{session_id}:ctx"


def load_openai_messages(
    *,
    db: Session,
    r: Redis,
    session_id: UUID,
    max_messages: int,
) -> list[dict[str, Any]]:
    raw = r.get(_redis_key(session_id))
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return list(data)[-max_messages:]
        except json.JSONDecodeError:
            pass

    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max_messages)
    ).all()
    rows = list(reversed(rows))
    return [message_to_openai(m) for m in rows]


def message_to_openai(m: ChatMessage) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": m.role, "content": m.content or ""}
    if m.tool_calls is not None:
        msg["tool_calls"] = m.tool_calls
    if m.tool_call_id:
        msg["tool_call_id"] = m.tool_call_id
    if m.tool_name and m.role == "tool":
        msg["name"] = m.tool_name
    return msg


def refresh_redis_cache(
    *,
    db: Session,
    r: Redis,
    session_id: UUID,
    max_messages: int,
) -> None:
    settings = get_settings()
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max_messages)
    ).all()
    rows = list(reversed(rows))
    payload = [message_to_openai(m) for m in rows]
    r.set(
        _redis_key(session_id),
        json.dumps(payload, default=str),
        ex=settings.session_redis_ttl_seconds,
    )


def append_user_message(
    *,
    db: Session,
    r: Redis,
    session_id: UUID,
    content: str,
) -> ChatMessage:
    row = ChatMessage(session_id=session_id, role="user", content=content)
    db.add(row)
    db.commit()
    db.refresh(row)
    refresh_redis_cache(
        db=db,
        r=r,
        session_id=session_id,
        max_messages=get_settings().session_context_max_messages,
    )
    return row


def append_assistant_message(
    *,
    db: Session,
    r: Redis,
    session_id: UUID,
    run_id: UUID,
    content: str,
    tool_calls: list[Any] | None = None,
) -> ChatMessage:
    row = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=content or "",
        tool_calls=tool_calls,
        run_id=run_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    refresh_redis_cache(
        db=db,
        r=r,
        session_id=session_id,
        max_messages=get_settings().session_context_max_messages,
    )
    return row


def append_tool_message(
    *,
    db: Session,
    r: Redis,
    session_id: UUID,
    run_id: UUID,
    tool_call_id: str,
    tool_name: str,
    content: str,
) -> ChatMessage:
    row = ChatMessage(
        session_id=session_id,
        role="tool",
        content=content,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        run_id=run_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    refresh_redis_cache(
        db=db,
        r=r,
        session_id=session_id,
        max_messages=get_settings().session_context_max_messages,
    )
    return row
