from __future__ import annotations

import logging
import re
from typing import Set

import httpx

from sayai.skillhunter.models import CrawlItem

logger = logging.getLogger(__name__)

DEFAULT_SKILLS_MAP_URL = (
    "https://raw.githubusercontent.com/midudev/autoskills/main/packages/autoskills/skills-map.ts"
)

# Quoted skill bundle id: org/repo or org/repo/subpath (no spaces, no http)
_SKILL_REF = re.compile(r'"((?:[a-zA-Z0-9_.-]+/){1,}[a-zA-Z0-9_.-]+)"')


class AutoskillsMapCrawler:
    """Extract GitHub repo targets from midudev/autoskills ``skills-map.ts`` (curated list)."""

    def __init__(self, map_url: str = DEFAULT_SKILLS_MAP_URL, *, max_items: int = 80) -> None:
        self.map_url = map_url.strip() or DEFAULT_SKILLS_MAP_URL
        self.max_items = max(1, max_items)

    def _parse_repo_keys(self, text: str) -> Set[tuple[str, str, str]]:
        """Return set of (org, repo, full_key) for dedupe."""
        seen: set[tuple[str, str]] = set()
        out: set[tuple[str, str, str]] = set()
        for m in _SKILL_REF.finditer(text):
            key = m.group(1)
            if key.startswith(("http://", "https://")):
                continue
            if "/" not in key:
                continue
            parts = key.split("/")
            if len(parts) < 2:
                continue
            org, repo = parts[0], parts[1]
            if not org or not repo:
                continue
            dedupe = (org.lower(), repo.lower())
            if dedupe in seen:
                continue
            seen.add(dedupe)
            out.add((org, repo, key))
            if len(out) >= self.max_items:
                break
        return out

    async def crawl(self) -> list[CrawlItem]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                r = await client.get(self.map_url)
                r.raise_for_status()
                text = r.text
            except Exception as e:
                logger.warning("autoskills map fetch %s: %s", self.map_url, e)
                return []

        items: list[CrawlItem] = []
        for org, repo, full_key in self._parse_repo_keys(text):
            url = f"https://github.com/{org}/{repo}"
            items.append(
                CrawlItem(
                    name=f"autoskills__{org}__{repo}".replace("/", "-"),
                    version="main",
                    url=url,
                    description=f"From autoskills skills-map: {full_key}",
                    readme="",
                    license_hint="",
                    source="autoskills_map",
                    extra={"map_key": full_key, "map_url": self.map_url},
                )
            )
        return items
