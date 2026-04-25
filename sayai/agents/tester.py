from __future__ import annotations

from pathlib import Path

from sayai.agents.base import BaseAgent


class TesterAgent(BaseAgent):
    def __init__(
        self,
        *,
        cwd: Path | None = None,
        session_id: str | None = None,
        shared_scratch: dict | None = None,
    ):
        super().__init__(
            "tester",
            cwd=cwd,
            session_id=session_id,
            shared_scratch=shared_scratch,
        )

    @property
    def llm_task_type(self) -> str:
        return "testing"

    @property
    def system_prompt(self) -> str:
        return """You are TesterAgent for SayAi — a QA engineer who writes and runs tests.

Tools:
<tool>read_file</tool><args>{"path": "path"}</args>
<tool>write_file</tool><args>{"path": "path", "content": "..."}</args>
<tool>run_tests</tool><args>{}</args>
<tool>bash</tool><args>{"command": "pytest -q"}</args>
<tool>lint</tool><args>{"path": "."}</args>
<tool>search_code</tool><args>{"query": "def ", "path": "."}</args>

Prefer pytest for Python. After writing tests, run them and report pass/fail.
If finished without tools, summarize coverage and results."""
