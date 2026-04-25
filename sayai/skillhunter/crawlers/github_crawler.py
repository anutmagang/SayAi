from __future__ import annotations

import os
from typing import Any

import httpx

from sayai.skillhunter.models import CrawlItem


class GitHubCrawler:
    """Search GitHub repositories (public API; optional GITHUB_TOKEN)."""

    def __init__(self, query: str, *, per_page: int = 15):
        self.query = query
        self.per_page = min(per_page, 30)

    async def crawl(self) -> list[CrawlItem]:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "SayAi-SkillHunter/0.4",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = "https://api.github.com/search/repositories"
        params = {"q": self.query, "sort": "stars", "per_page": str(self.per_page)}
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.get(url, params=params, headers=headers)
            if r.status_code == 403:
                return []
            r.raise_for_status()
            data = r.json()

        out: list[CrawlItem] = []
        for it in data.get("items", [])[: self.per_page]:
            raw_lic = it.get("license")
            if isinstance(raw_lic, dict):
                lic_spdx = str(raw_lic.get("spdx_id") or "")
            elif isinstance(raw_lic, str):
                lic_spdx = raw_lic
            else:
                lic_spdx = ""
            out.append(
                CrawlItem(
                    name=str(it.get("full_name", "unknown")).replace("/", "__"),
                    version=str(it.get("default_branch", "main")),
                    url=str(it.get("html_url", "")),
                    description=str(it.get("description") or ""),
                    readme="",
                    license_hint=lic_spdx or "unknown",
                    source="github",
                    extra={
                        "stars": it.get("stargazers_count"),
                        "topics": it.get("topics", []),
                        "pushed_at": it.get("pushed_at"),
                    },
                )
            )
        return out
