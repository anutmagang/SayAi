from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from sayai.config import load_config
from sayai.llm import LLMClient
from sayai.memory.context import ContextManager
from sayai.tools import ToolExecutor


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: str,
        *,
        cwd: Path | None = None,
        session_id: str | None = None,
        shared_scratch: dict[str, Any] | None = None,
    ):
        self.id = agent_id
        self.cwd = (cwd or Path.cwd()).resolve()
        self.llm = LLMClient()
        self.tools = ToolExecutor(
            cwd=self.cwd,
            session_id=session_id,
            shared_scratch=shared_scratch,
        )
        self.context = ContextManager(agent_id)
        self._settings = load_config()
        self.max_iterations = self._settings.agents.max_iterations

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def llm_task_type(self) -> str:
        """Routing key for SmartRouter (coding, reviewing, …)."""
        raise NotImplementedError

    def _format_user_task(self, task: str, ctx: dict[str, Any]) -> str:
        parts = [f"Task:\n{task}"]
        if ctx.get("summary"):
            parts.append(f"Summary: {ctx['summary']}")
        parts.append(f"Working directory: {self.cwd}")
        if ctx.get("scratch") is not None:
            parts.append(f"Scratchpad: {ctx['scratch']}")
        return "\n\n".join(parts)

    def _resolve_llm_task_type(self, ctx: dict[str, Any]) -> str:
        return str(ctx.get("force_task_type") or self.llm_task_type)

    async def run(self, task: str, context: dict[str, Any] | None = None) -> str:
        chunks: list[str] = []
        async for part in self.run_stream(task, context=context):
            chunks.append(part)
        return "".join(chunks)

    async def run_stream(self, task: str, context: dict[str, Any] | None = None) -> AsyncIterator[str]:
        ctx = dict(context or {})
        budget = str(ctx.get("budget", "normal"))
        ttype = self._resolve_llm_task_type(ctx)

        self.context.clear()
        self.context.add("system", self.system_prompt)
        self.context.add("user", self._format_user_task(task, ctx))

        for i in range(self.max_iterations):
            yield f"\n[{self.id} {i + 1}/{self.max_iterations}]\n"
            messages = self.context.get_messages()
            full = await self.llm.complete(messages=messages, task_type=ttype, budget=budget)
            yield full

            if "<tool>" in full:
                self.context.add("assistant", full)
                tool_result = await self.tools.execute(full)
                yield f"\n── tool ──\n{tool_result[:8000]}\n"
                self.context.add("user", f"Tool output:\n{tool_result}\nContinue the task.")
            else:
                return

        yield "\n[max iterations reached]\n"
