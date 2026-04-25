from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sayai.agents.coder import CoderAgent
from sayai.config import load_config
from sayai.orchestrator.aggregator import Aggregator
from sayai.orchestrator.dag import DAGExecutor
from sayai.orchestrator.planner import Planner
from sayai.orchestrator.pool import AgentPool
from sayai.orchestrator.task import tasks_from_plan


class Orchestrator:
    """Planner → DAG (parallel waves) → Aggregator, or single-agent mode."""

    def __init__(self, cwd: Path | None = None, *, use_dag: bool | None = None):
        self.cwd = (cwd or Path.cwd()).resolve()
        self._settings = load_config()
        self._use_dag_override = use_dag

    def _use_dag(self) -> bool:
        if self._use_dag_override is not None:
            return self._use_dag_override
        return self._settings.orchestrator.use_dag

    async def stream(self, task: str) -> AsyncIterator[str]:
        session_id = str(uuid.uuid4())
        shared_scratch: dict[str, Any] = {}

        if self._settings.memory.redis_url.strip():
            from sayai.memory.scratchpad import RedisScratchpad

            remote = await RedisScratchpad(session_id).hgetall()
            shared_scratch.update(remote)

        if not self._use_dag():
            agent = CoderAgent(
                cwd=self.cwd,
                session_id=session_id,
                shared_scratch=shared_scratch,
            )
            async for chunk in agent.run_stream(task):
                yield chunk
            if self._settings.memory.redis_url.strip():
                from sayai.memory.scratchpad import RedisScratchpad

                flat = {str(k): str(v) for k, v in shared_scratch.items()}
                if flat:
                    await RedisScratchpad(session_id).hset(flat)
            return

        yield "[sayai] Planning…\n"
        planner = Planner()
        specs = await planner.plan_safe(task)
        yield json.dumps(specs, indent=2) + "\n"

        tasks = tasks_from_plan(specs)
        if not tasks:
            yield "[sayai] Planner returned no tasks; stopping.\n"
            return

        pool = AgentPool(
            cwd=self.cwd,
            session_id=session_id,
            shared_scratch=shared_scratch,
        )
        dag = DAGExecutor(pool, scratch=shared_scratch)

        try:
            async for wave, ids in dag.execute_stream(tasks):
                yield f"\n--- wave {wave} completed: {ids} ---\n"
                for tid in ids:
                    body = str(dag.results.get(tid, ""))
                    preview = body[:2500] + ("…" if len(body) > 2500 else "")
                    yield f"\n### `{tid}`\n{preview}\n"
        except Exception as e:
            yield f"\n[DAG error] {e!s}\n"
            return

        if self._settings.memory.redis_url.strip():
            from sayai.memory.scratchpad import RedisScratchpad

            flat = {str(k): str(v) for k, v in shared_scratch.items()}
            if flat:
                await RedisScratchpad(session_id).hset(flat)

        yield "\n[sayai] Aggregating…\n"
        merged = await Aggregator().merge(task, dag.results)
        yield merged

        if self._settings.features.reflect_after_dag:
            yield "\n[sayai] Reflection…\n"
            from sayai.llm import LLMClient

            reflect_prompt = (
                "You are a concise reviewer. Given the original task and the merged agent output, "
                "list 3–7 bullet risks, gaps, or follow-ups. No preamble.\n\n"
                f"TASK:\n{task}\n\nMERGED OUTPUT:\n{merged[:12000]}"
            )
            client = LLMClient()
            reflection = await client.complete(
                [{"role": "user", "content": reflect_prompt}],
                task_type="reviewing",
                budget="cheap",
            )
            yield reflection + "\n"

    async def run(self, task: str) -> str:
        parts: list[str] = []
        async for c in self.stream(task):
            parts.append(c)
        return "".join(parts)
