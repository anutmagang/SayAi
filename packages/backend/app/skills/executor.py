from __future__ import annotations

import concurrent.futures
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.config import get_settings
from app.skills.records import SkillRecord

_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="sayai_skill")


def execute_skill(
    skill: SkillRecord,
    arguments_json: str,
    *,
    session_message_count: int | None = None,
) -> dict[str, Any]:
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        return {"error": "invalid_tool_arguments_json"}

    settings = get_settings()
    timeout = max(1.0, float(settings.skill_tool_timeout_seconds))

    def _run() -> dict[str, Any]:
        if skill.id == "sayai.memory_len" or skill.extends_skill_id == "sayai.memory_len":
            return {"message_count": session_message_count or 0}
        return skill.handler(args)

    fut = _executor.submit(_run)
    try:
        return fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return {"error": "skill_execution_timeout"}
