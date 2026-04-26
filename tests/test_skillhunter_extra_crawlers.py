from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sayai.skillhunter.crawlers.awesome_crawler import AwesomeMarkdownCrawler
from sayai.skillhunter.crawlers.clawhub_crawler import ClawHubConvexCrawler


def test_awesome_extract_github_urls() -> None:
    c = AwesomeMarkdownCrawler([])
    md = """
    - [MCP](https://github.com/org/cool-mcp) — tool
    See also https://github.com/other/legacy.git for legacy.
    Dup: https://github.com/org/cool-mcp/issues/1
    """
    pairs = c._extract(md, max_pairs=20)
    owners_repos = {(a, b) for a, b in pairs}
    assert ("org", "cool-mcp") in owners_repos
    assert ("other", "legacy") in owners_repos


@pytest.mark.asyncio
async def test_clawhub_crawl_parses_page() -> None:
    page_row = {
        "ownerHandle": "acme",
        "latestVersion": {"_id": "ver123", "version": "1.0.0"},
        "skill": {
            "slug": "demo-skill",
            "summary": "A demo",
            "latestVersionId": "ver123",
            "stats": {"downloads": 10, "stars": 2},
        },
    }
    list_json = {
        "status": "success",
        "value": {"hasMore": False, "page": [page_row]},
    }
    readme_json = {"status": "success", "value": {"path": "SKILL.md", "text": "# Hello"}}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock()

    async def _post(url: str, **kwargs: object) -> MagicMock:
        r = MagicMock()
        r.raise_for_status = MagicMock()
        if url.endswith("/api/query"):
            r.json = MagicMock(return_value=list_json)
        else:
            r.json = MagicMock(return_value=readme_json)
        return r

    mock_client.post.side_effect = _post
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("sayai.skillhunter.crawlers.clawhub_crawler.httpx.AsyncClient", return_value=mock_client):
        c = ClawHubConvexCrawler(
            convex_url="https://example.convex.cloud",
            num_per_page=5,
            max_pages=1,
            fetch_readme=True,
            delay_sec=0,
        )
        items = await c.crawl()

    assert len(items) == 1
    assert items[0].source == "clawhub"
    assert items[0].url == "https://clawhub.ai/acme/demo-skill"
    assert "Hello" in items[0].readme


@pytest.mark.asyncio
async def test_awesome_crawl_mock_http() -> None:
    body = "Link: https://github.com/foo/bar\n"
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.text = body

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("sayai.skillhunter.crawlers.awesome_crawler.httpx.AsyncClient", return_value=mock_client):
        c = AwesomeMarkdownCrawler(["https://example.com/readme.md"], max_repos=5)
        items = await c.crawl()

    assert len(items) == 1
    assert items[0].url == "https://github.com/foo/bar"
    assert items[0].source == "awesome"
