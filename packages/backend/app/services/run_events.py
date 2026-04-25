from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from redis import Redis


def emit_event(r: Redis, run_id: UUID, event: dict[str, Any]) -> None:
    key = f"run:{run_id}:events"
    channel = f"run:{run_id}:notify"
    payload = json.dumps(event, default=str)
    r.rpush(key, payload)
    r.publish(channel, "1")
