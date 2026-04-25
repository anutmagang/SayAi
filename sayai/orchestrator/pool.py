from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from sayai.agents.base import BaseAgent
from sayai.agents.coder import CoderAgent
from sayai.agents.reviewer import ReviewerAgent
from sayai.agents.searcher import SearcherAgent
from sayai.agents.tester import TesterAgent
from sayai.orchestrator.task import Task


class AgentPool:
    """Maps DAG task.agent_type to runnable agents."""

    def __init__(
        self,
        cwd: Path | None = None,
        *,
        session_id: str | None = None,
        shared_scratch: dict[str, Any] | None = None,
    ):
        self.cwd = (cwd or Path.cwd()).resolve()
        self.session_id = session_id or "default"
        self.shared_scratch: dict[str, Any] = (
            shared_scratch if shared_scratch is not None else {}
        )
        self._registry: dict[str, Callable[[], BaseAgent]] = {
            "coder": lambda: CoderAgent(
                cwd=self.cwd,
                session_id=self.session_id,
                shared_scratch=self.shared_scratch,
            ),
            "reviewer": lambda: ReviewerAgent(
                cwd=self.cwd,
                session_id=self.session_id,
                shared_scratch=self.shared_scratch,
            ),
            "searcher": lambda: SearcherAgent(
                cwd=self.cwd,
                session_id=self.session_id,
                shared_scratch=self.shared_scratch,
            ),
            "tester": lambda: TesterAgent(
                cwd=self.cwd,
                session_id=self.session_id,
                shared_scratch=self.shared_scratch,
            ),
            "planner": lambda: CoderAgent(
                cwd=self.cwd,
                session_id=self.session_id,
                shared_scratch=self.shared_scratch,
            ),
        }

    def _enrich_instruction(self, task: Task, dag_results: dict[str, str]) -> str:
        if not task.depends_on:
            return task.instruction
        parts: list[str] = []
        for dep in task.depends_on:
            if dep in dag_results:
                body = str(dag_results[dep])
                if len(body) > 12_000:
                    body = body[:12_000] + "\n…(truncated)"
                parts.append(f"### From task `{dep}`\n{body}")
        if not parts:
            return task.instruction
        return task.instruction + "\n\n## Upstream outputs\n" + "\n\n".join(parts)

    async def run(
        self,
        task: Task,
        *,
        dag_results: dict[str, str],
        scratch: dict[str, Any] | None = None,
        retry: bool = False,
    ) -> str:
        scratch = scratch if scratch is not None else {}
        factory = self._registry.get(task.agent_type, self._registry["coder"])
        agent = factory()
        text = self._enrich_instruction(task, dag_results)
        merged_scratch = {**self.shared_scratch, **scratch}
        ctx: dict[str, Any] = {
            "budget": task.budget,
            "dag_results": dag_results,
            "scratch": merged_scratch,
            "cwd": str(self.cwd),
        }
        if task.agent_type == "planner":
            ctx["force_task_type"] = "planning"
            text = (
                "You are a planning sub-agent. Produce a concise plan or decomposition only; "
                "do not write large code blocks unless asked.\n\n" + text
            )
        try:
            return await agent.run(text, context=ctx)
        except Exception:
            if retry:
                raise
            return await self.run(
                task, dag_results=dag_results, scratch=scratch, retry=True
            )
