from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator

from sayai.llm import LLMClient

PLANNER_SYSTEM_PROMPT = """You are the AI Planner for SayAi — an agentic coding platform.

Decompose the user's task into specific subtasks that specialized agents can run in parallel when possible.

OUTPUT: a single JSON array only. No markdown fences, no other text.

Each element:
{
  "id": "unique_snake_id",
  "agent_type": "coder" | "reviewer" | "searcher" | "tester" | "planner",
  "instruction": "clear actionable instruction for that agent",
  "depends_on": ["ids_of_tasks_that_must_finish_first"],
  "priority": 1,
  "budget": "cheap" | "normal" | "premium"
}

Rules:
- Parallelize independent work (empty depends_on when possible).
- Use "searcher" for research, external docs, or web lookup.
- Use "coder" for implementation; "tester" for tests; "reviewer" for review/security.
- "tester" tasks should depend_on the coder task that produces the code under test.
- "reviewer" can depend_on relevant coder tasks.
- budget: cheap for quick lookup, normal for coding, premium for deep review/planning.
- At least 1 task; at most 12 tasks.
- Every depends_on id must match another task's id in the same array (or be empty).
"""


class PlanTaskSpec(BaseModel):
    id: str
    agent_type: str
    instruction: str
    depends_on: list[str] = Field(default_factory=list)
    priority: int = 5
    budget: str = "normal"

    @field_validator("agent_type")
    @classmethod
    def _agent(cls, v: str) -> str:
        allowed = {"coder", "reviewer", "searcher", "tester", "planner"}
        if v not in allowed:
            return "coder"
        return v

    @field_validator("budget")
    @classmethod
    def _budget(cls, v: str) -> str:
        if v not in ("cheap", "normal", "premium"):
            return "normal"
        return v


def _strip_json_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def _parse_plan_list(raw: str) -> list[dict[str, Any]]:
    data = json.loads(_strip_json_fence(raw))
    if isinstance(data, dict) and "tasks" in data:
        data = data["tasks"]
    if not isinstance(data, list):
        raise ValueError("plan JSON must be an array")
    return data


class Planner:
    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()

    async def plan(self, user_task: str) -> list[dict[str, Any]]:
        response = await self.client.complete(
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": f"User task:\n{user_task}"},
            ],
            task_type="planning",
            budget="premium",
        )
        items = _parse_plan_list(response)
        validated: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            instr = str(item.get("instruction", "")).strip()
            if not instr:
                continue
            spec = PlanTaskSpec.model_validate(
                {
                    "id": item.get("id", f"task_{len(validated)}"),
                    "agent_type": item.get("agent_type", "coder"),
                    "instruction": instr,
                    "depends_on": item.get("depends_on") or [],
                    "priority": item.get("priority", 5),
                    "budget": item.get("budget", "normal"),
                }
            )
            validated.append(spec.model_dump())
        return validated

    async def plan_safe(self, user_task: str) -> list[dict[str, Any]]:
        try:
            out = await self.plan(user_task)
            if not out:
                raise ValueError("empty plan")
            ids = {t["id"] for t in out}
            for t in out:
                t["depends_on"] = [d for d in t["depends_on"] if d in ids]
            return out
        except Exception:
            return [
                {
                    "id": "solo_coder",
                    "agent_type": "coder",
                    "instruction": user_task,
                    "depends_on": [],
                    "priority": 1,
                    "budget": "normal",
                }
            ]
