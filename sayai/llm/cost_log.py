from __future__ import annotations

import json
import time
from typing import Any

import aiofiles

from sayai.config import load_config


def _usage_to_dict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return dict(usage)
    out: dict[str, Any] = {}
    for k in ("prompt_tokens", "completion_tokens", "total_tokens"):
        v = getattr(usage, k, None)
        if v is not None:
            out[k] = v
    return out


async def maybe_log_litellm_usage(response: Any) -> None:
    """Append one JSON line per completion when features.cost_log_path is set."""
    cfg = load_config()
    path = (cfg.features.cost_log_path or "").strip()
    if not path or response is None:
        return
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    model = getattr(response, "model", None) or ""
    line = json.dumps(
        {
            "ts": time.time(),
            "model": model,
            "usage": _usage_to_dict(usage),
        },
        ensure_ascii=False,
    )
    async with aiofiles.open(path, "a", encoding="utf-8") as f:
        await f.write(line + "\n")
