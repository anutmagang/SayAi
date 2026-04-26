from __future__ import annotations

import pytest

from sayai.tools.executor import ToolExecutor


def test_normalize_web_search_aliases() -> None:
    ex = ToolExecutor.__new__(ToolExecutor)  # type: ignore[misc]
    a = ex._normalize_tool_args("web_search", {"q": "hello world"})
    assert a == {"query": "hello world"}


def test_normalize_retrieve_codebase_directory_to_path() -> None:
    ex = ToolExecutor.__new__(ToolExecutor)  # type: ignore[misc]
    a = ex._normalize_tool_args(
        "retrieve_codebase", {"query": "foo", "directory": "/tmp/x"}
    )
    assert a["query"] == "foo"
    assert a["path"] == "/tmp/x"
    assert "directory" not in a


@pytest.mark.asyncio
async def test_execute_web_search_rejects_empty_query() -> None:
    ex = ToolExecutor(cwd=__import__("pathlib").Path("."))
    out = await ex.execute('<tool>web_search</tool><args>{}</args>')
    assert "Error" in out and "query" in out.lower()
