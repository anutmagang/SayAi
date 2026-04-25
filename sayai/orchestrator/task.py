from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    agent_type: str
    instruction: str
    depends_on: list[str] = field(default_factory=list)
    priority: int = 5
    budget: str = "normal"
    result: Any = None


def tasks_from_plan(specs: list[dict[str, Any]]) -> list[Task]:
    return [
        Task(
            id=s["id"],
            agent_type=s["agent_type"],
            instruction=s.get("instruction") or "",
            depends_on=list(s.get("depends_on", [])),
            priority=int(s.get("priority", 5)),
            budget=str(s.get("budget", "normal")),
        )
        for s in specs
    ]
