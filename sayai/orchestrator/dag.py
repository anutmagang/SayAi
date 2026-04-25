from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from sayai.orchestrator.pool import AgentPool
from sayai.orchestrator.task import Task


class DAGError(RuntimeError):
    pass


class DAGExecutor:
    """Runs tasks in parallel waves respecting depends_on (blueprint §5)."""

    def __init__(self, pool: AgentPool, scratch: dict[str, Any] | None = None):
        self.pool = pool
        self.scratch: dict[str, Any] = scratch if scratch is not None else {}
        self.results: dict[str, Any] = {}

    def _ready(self, pending: dict[str, Task]) -> list[Task]:
        return [
            t
            for t in pending.values()
            if all(dep in self.results for dep in t.depends_on)
        ]

    async def _run_wave(self, ready: list[Task]) -> None:
        ready.sort(key=lambda t: (t.priority, t.id))

        async def _one(task: Task) -> tuple[str, Any]:
            try:
                r = await self.pool.run(
                    task, dag_results=self.results, scratch=self.scratch, retry=False
                )
                return task.id, r
            except Exception:
                r = await self.pool.run(
                    task, dag_results=self.results, scratch=self.scratch, retry=True
                )
                return task.id, r

        pairs: list[Any | BaseException] = await asyncio.gather(
            *[_one(t) for t in ready], return_exceptions=True
        )
        for item in pairs:
            if isinstance(item, BaseException):
                raise item
            tid, result = item
            self.results[tid] = result

    async def execute(self, tasks: list[Task]) -> dict[str, Any]:
        self.results = {}
        pending = {t.id: t for t in tasks}

        while pending:
            ready = self._ready(pending)
            if not ready:
                if pending:
                    raise DAGError(
                        f"Circular or unsatisfiable dependencies; pending: {list(pending.keys())}"
                    )
                break
            await self._run_wave(ready)
            for t in ready:
                del pending[t.id]

        return self.results

    async def execute_stream(self, tasks: list[Task]) -> AsyncIterator[tuple[int, list[str]]]:
        """Yields (wave_index, task_ids) after each parallel wave completes."""
        self.results = {}
        pending = {t.id: t for t in tasks}
        wave = 0
        while pending:
            ready = self._ready(pending)
            if not ready:
                if pending:
                    raise DAGError(
                        f"Circular or unsatisfiable dependencies; pending: {list(pending.keys())}"
                    )
                break
            await self._run_wave(ready)
            yield wave, [t.id for t in ready]
            for t in ready:
                del pending[t.id]
            wave += 1
