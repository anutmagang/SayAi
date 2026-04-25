from __future__ import annotations

from pathlib import Path

from sayai.agents.base import BaseAgent


class SearcherAgent(BaseAgent):
    def __init__(
        self,
        *,
        cwd: Path | None = None,
        session_id: str | None = None,
        shared_scratch: dict | None = None,
    ):
        super().__init__(
            "searcher",
            cwd=cwd,
            session_id=session_id,
            shared_scratch=shared_scratch,
        )

    @property
    def llm_task_type(self) -> str:
        return "searching"

    @property
    def system_prompt(self) -> str:
        return """You are SearcherAgent for SayAi — research and retrieval specialist.

Tools:
<tool>web_search</tool><args>{"query": "keywords"}</args>
<tool>fetch_url</tool><args>{"url": "https://..."}</args>
<tool>search_code</tool><args>{"query": "symbol", "path": "."}</args>
<tool>retrieve_codebase</tool><args>{"query": "phrase", "path": ".", "max_files": 5}</args>
<tool>vector_search</tool><args>{"query": "embedding query", "top_k": 6}</args>
<tool>read_file</tool><args>{"path": "path"}</args>
<tool>scratch_set</tool><args>{"key": "research_notes", "value": "..."}</args>

Basic RAG: use retrieve_codebase for broad codebase context, then read_file for detail.
Cite URLs for web findings. If no tools are needed, give a concise research summary."""
