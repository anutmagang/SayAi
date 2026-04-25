from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from litellm import completion
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.redis_client import get_sync_redis
from app.db.models.run import Run
from app.db.models.run_step import RunStep
from app.db.session import get_session_factory
from app.services import memory
from app.services.run_events import emit_event
from app.services.skill_policy import load_skills_for_user
from app.skills.executor import execute_skill
from app.skills.records import SkillRecord
from app.skills.registry import (
    filter_skills,
    resolve_skill_id,
    tools_openai_schema,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _jsonify(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _message_to_dict(message: Any) -> dict[str, Any]:
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    if isinstance(message, dict):
        return message
    return dict(message)


def _add_step(
    *,
    db: Session,
    r,
    run_id: UUID,
    seq_holder: list[int],
    step_type: str,
    name: str,
    detail: dict[str, Any] | None,
    status: str = "completed",
    error: str | None = None,
) -> None:
    seq = seq_holder[0]
    seq_holder[0] = seq + 1
    step = RunStep(
        run_id=run_id,
        seq=seq,
        step_type=step_type,
        name=name,
        status=status,
        detail=detail,
        error=error,
        ended_at=_now(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    emit_event(
        r,
        run_id,
        {
            "type": "step",
            "step": {
                "id": str(step.id),
                "seq": step.seq,
                "step_type": step.step_type,
                "name": step.name,
                "status": step.status,
                "detail": step.detail,
                "error": step.error,
            },
        },
    )


def execute_run(run_id: UUID) -> None:
    settings = get_settings()
    r = get_sync_redis()
    factory = get_session_factory()
    db = factory()
    seq_holder = [1]

    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        if run.status != "pending":
            return

        summary = run.summary or {}
        allowlist = list(summary.get("skill_allowlist") or ["*"])
        max_llm_calls = int(summary.get("max_llm_calls") or settings.agent_max_steps)
        tools_enabled = bool(summary.get("tools_enabled", True))

        run.status = "running"
        db.add(run)
        db.commit()

        emit_event(r, run_id, {"type": "run.started", "run_id": str(run_id), "mode": run.mode})

        messages: list[dict[str, Any]] = memory.load_openai_messages(
            db=db,
            r=r,
            session_id=run.session_id,
            max_messages=settings.session_context_max_messages,
        )
        system_msg = {
            "role": "system",
            "content": "You are SayAi, a helpful assistant. Use tools when they help.",
        }
        messages = [system_msg, *messages]

        all_skills = load_skills_for_user(db, run.user_id)
        skills = filter_skills(allowlist, all_skills)
        tools, fn_index = tools_openai_schema(skills)
        tools_enabled = tools_enabled and bool(tools)
        skill_by_id: dict[str, SkillRecord] = {s.id: s for s in skills}

        prompt_tokens = 0
        completion_tokens = 0
        final_text = ""

        for _ in range(max(1, max_llm_calls)):
            kwargs: dict[str, Any] = {
                "model": run.model,
                "messages": messages,
                "temperature": 0.2,
            }
            if tools_enabled:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            try:
                resp = completion(**kwargs)
            except Exception as exc:
                logger.exception("LLM completion failed")
                run.status = "failed"
                run.error = str(exc)
                run.completed_at = _now()
                db.add(run)
                db.commit()
                emit_event(r, run_id, {"type": "error", "message": str(exc)})
                _add_step(
                    db=db,
                    r=r,
                    run_id=run_id,
                    seq_holder=seq_holder,
                    step_type="llm",
                    name="completion",
                    detail={"model": run.model, "error": str(exc)},
                    status="failed",
                    error=str(exc),
                )
                return

            usage = getattr(resp, "usage", None)
            if usage is not None:
                prompt_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                completion_tokens += int(getattr(usage, "completion_tokens", 0) or 0)

            assistant_msg = _jsonify(_message_to_dict(resp.choices[0].message))
            tool_calls = assistant_msg.get("tool_calls")
            content = assistant_msg.get("content") or ""

            emit_event(
                r,
                run_id,
                {
                    "type": "assistant.message",
                    "content": content,
                    "tool_calls": tool_calls,
                },
            )

            _add_step(
                db=db,
                r=r,
                run_id=run_id,
                seq_holder=seq_holder,
                step_type="llm",
                name="completion",
                detail={"model": run.model, "tool_calls": tool_calls, "content": content},
            )

            messages.append(assistant_msg)

            if not tool_calls:
                final_text = content
                memory.append_assistant_message(
                    db=db,
                    r=r,
                    session_id=run.session_id,
                    run_id=run.id,
                    content=final_text,
                    tool_calls=None,
                )
                break

            tool_calls_json = _jsonify(tool_calls)
            memory.append_assistant_message(
                db=db,
                r=r,
                session_id=run.session_id,
                run_id=run.id,
                content=content or "",
                tool_calls=tool_calls_json,
            )

            for call in tool_calls:
                fn = call.get("function", {}) if isinstance(call, dict) else {}
                fn_name = fn.get("name")
                fn_args = fn.get("arguments") or "{}"
                tool_call_id = call.get("id") or ""

                emit_event(
                    r,
                    run_id,
                    {
                        "type": "tool.call",
                        "name": fn_name,
                        "arguments": fn_args,
                        "tool_call_id": tool_call_id,
                    },
                )

                skill_id = resolve_skill_id(str(fn_name), fn_index) if fn_name else None
                if skill_id is None or skill_id not in skill_by_id:
                    result = {"error": f"Unknown tool: {fn_name}"}
                else:
                    result = execute_skill(
                        skill_by_id[skill_id],
                        str(fn_args),
                        session_message_count=len(messages),
                    )

                emit_event(
                    r,
                    run_id,
                    {
                        "type": "tool.result",
                        "name": fn_name,
                        "tool_call_id": tool_call_id,
                        "content": result,
                    },
                )

                _add_step(
                    db=db,
                    r=r,
                    run_id=run_id,
                    seq_holder=seq_holder,
                    step_type="tool",
                    name=str(fn_name or "tool"),
                    detail={"skill_id": skill_id, "arguments": fn_args, "result": result},
                )

                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": str(skill_id or fn_name or "tool"),
                    "content": json.dumps(result, default=str),
                }
                messages.append(tool_msg)

                memory.append_tool_message(
                    db=db,
                    r=r,
                    session_id=run.session_id,
                    run_id=run.id,
                    tool_call_id=str(tool_call_id),
                    tool_name=str(skill_id or fn_name or "tool"),
                    content=tool_msg["content"],
                )
        else:
            final_text = "Max LLM/tool rounds reached without a final answer."
            memory.append_assistant_message(
                db=db,
                r=r,
                session_id=run.session_id,
                run_id=run.id,
                content=final_text,
                tool_calls=None,
            )

        run.status = "completed"
        run.prompt_tokens = prompt_tokens
        run.completion_tokens = completion_tokens
        run.completed_at = _now()
        merged_summary = dict(run.summary or {})
        merged_summary["assistant"] = final_text
        run.summary = merged_summary
        db.add(run)
        db.commit()

        emit_event(
            r,
            run_id,
            {
                "type": "run.completed",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        )
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Run worker crashed")
        try:
            run = db.get(Run, run_id)
            if run is not None:
                run.status = "failed"
                run.error = str(exc)
                run.completed_at = _now()
                db.add(run)
                db.commit()
            emit_event(r, run_id, {"type": "error", "message": str(exc)})
        except Exception:
            logger.exception("Failed to persist run failure")
    finally:
        db.close()
