from __future__ import annotations

from pathlib import Path

from sayai.agents.base import BaseAgent


class ReviewerAgent(BaseAgent):
    def __init__(
        self,
        *,
        cwd: Path | None = None,
        session_id: str | None = None,
        shared_scratch: dict | None = None,
    ):
        super().__init__(
            "reviewer",
            cwd=cwd,
            session_id=session_id,
            shared_scratch=shared_scratch,
        )

    @property
    def llm_task_type(self) -> str:
        return "reviewing"

    @property
    def system_prompt(self) -> str:
        return """You are ReviewerAgent for SayAi — a senior code reviewer focused on security and quality.

Use tools when you need evidence:
<tool>read_file</tool><args>{"path": "relative/path"}</args>
<tool>search_code</tool><args>{"query": "pattern", "path": "."}</args>
<tool>lint</tool><args>{"path": "src"}</args>
<tool>lsp_diagnostics</tool><args>{"path": "file.py"}</args>
<tool>git_diff</tool><args>{}</args>
<tool>vector_search</tool><args>{"query": "topic", "top_k": 5}</args>
<tool>bash</tool><args>{"command": "ruff check ."}</args>

Output structure:
## Review
### CRITICAL / WARNING / SUGGESTION
### SUMMARY

If no tools are needed, answer directly with the same structure."""
