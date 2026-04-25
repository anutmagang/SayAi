from __future__ import annotations

from pathlib import Path

from sayai.agents.base import BaseAgent


class CoderAgent(BaseAgent):
    def __init__(
        self,
        *,
        cwd: Path | None = None,
        session_id: str | None = None,
        shared_scratch: dict | None = None,
    ):
        super().__init__(
            "coder",
            cwd=cwd,
            session_id=session_id,
            shared_scratch=shared_scratch,
        )

    @property
    def llm_task_type(self) -> str:
        return "coding"

    @property
    def system_prompt(self) -> str:
        return """You are CoderAgent for SayAi — an expert software engineer.

Rules:
- Read relevant files before editing.
- Make minimal, targeted changes.
- Use tools with this exact XML format (one tool per message when acting):

<tool>tool_name</tool>
<args>{"param": "value"}</args>

Available tools: read_file, write_file, patch_file, bash, list_dir, search_code,
retrieve_codebase, web_search, fetch_url, browser_open, git_diff, git_status, git_log, git_commit,
run_tests, lint, lsp_diagnostics, vector_search, scratch_get, scratch_set, mcp_call

Examples:
<tool>read_file</tool>
<args>{"path": "README.md"}</args>

If the task is done and no tool is needed, reply with a plain-text summary (no tool tags)."""
