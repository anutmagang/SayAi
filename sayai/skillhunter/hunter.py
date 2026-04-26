from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from sayai.config import load_config
from sayai.db import database as db_module
from sayai.db.skill_store import SkillStore
from sayai.skillhunter.analyzer import SkillAnalyzer
from sayai.skillhunter.crawlers import (
    AwesomeMarkdownCrawler,
    ClawHubConvexCrawler,
    GitHubCrawler,
    MCPRegistryCrawler,
    PyPICrawler,
)
from sayai.skillhunter.crawlers.autoskills_map_crawler import (
    DEFAULT_SKILLS_MAP_URL,
    AutoskillsMapCrawler,
)
from sayai.skillhunter.stack_profile import StackProfile, stack_relevance_boost
from sayai.skillhunter.models import CrawlItem
from sayai.skillhunter.notifier import HuntNotifier
from sayai.skillhunter.rewriter import SkillRewriter

logger = logging.getLogger(__name__)


class SkillHunter:
    """Phase 4 SkillHunter pipeline (blueprint §11)."""

    def __init__(self) -> None:
        self._cfg = load_config().skillhunter
        self.store = SkillStore()
        self.analyzer = SkillAnalyzer()
        self.rewriter = SkillRewriter()
        self.notifier = HuntNotifier()

    def _crawlers(self) -> list[Any]:
        crawlers: list[Any] = [
            GitHubCrawler(self._cfg.github_query, per_page=15),
            PyPICrawler(self._cfg.pypi_query, max_packages=12),
            MCPRegistryCrawler(self._cfg.mcp_registry_url, max_items=18),
        ]
        if self._cfg.clawhub_enabled:
            crawlers.append(
                ClawHubConvexCrawler(
                    convex_url=self._cfg.clawhub_convex_url,
                    sort=self._cfg.clawhub_sort,
                    num_per_page=self._cfg.clawhub_num_per_page,
                    max_pages=self._cfg.clawhub_max_pages,
                    fetch_readme=self._cfg.clawhub_fetch_readme,
                    delay_sec=self._cfg.clawhub_delay_sec,
                    non_suspicious_only=self._cfg.clawhub_non_suspicious_only,
                )
            )
        if self._cfg.awesome_enabled and self._cfg.awesome_raw_readme_urls:
            crawlers.append(
                AwesomeMarkdownCrawler(
                    list(self._cfg.awesome_raw_readme_urls),
                    max_repos=self._cfg.awesome_max_repos,
                )
            )
        if self._cfg.autoskills_map_enabled:
            map_url = (self._cfg.autoskills_map_url or "").strip() or DEFAULT_SKILLS_MAP_URL
            crawlers.append(
                AutoskillsMapCrawler(map_url, max_items=self._cfg.autoskills_map_max_items)
            )
        return crawlers

    async def hunt(self, cwd: Path | None = None) -> dict[str, int]:
        if not self._cfg.enabled:
            logger.info("SkillHunter disabled in config")
            return {"items": 0, "proposed": 0}

        root = (cwd or Path.cwd()).resolve()
        profile = (
            StackProfile.detect(root)
            if self._cfg.stack_detection_enabled
            else StackProfile()
        )

        crawlers = self._crawlers()
        raw_batches = await asyncio.gather(
            *[c.crawl() for c in crawlers],
            return_exceptions=True,
        )
        items: list[CrawlItem] = []
        for batch in raw_batches:
            if isinstance(batch, Exception):
                logger.warning("crawler error: %s", batch)
                continue
            items.extend(batch)

        proposed = 0
        seen_url: set[str] = set()
        for item in items:
            if item.url in seen_url:
                continue
            seen_url.add(item.url)
            try:
                if await self.store.exists_source_url(item.url):
                    continue
                analysis = await self.analyzer.analyze(
                    item, stack_summary=profile.summary if self._cfg.stack_detection_enabled else ""
                )
                if analysis.is_duplicate:
                    continue
                boost = (
                    stack_relevance_boost(item.name, item.description, item.url, profile)
                    if self._cfg.stack_detection_enabled
                    else 0.0
                )
                effective = min(1.0, float(analysis.score) + boost)
                if effective < self._cfg.min_score:
                    continue
                if not analysis.safety_ok or not analysis.recommended:
                    continue
                lic = (analysis.license or "").lower()
                if lic in ("unknown", "proprietary", "no-license", ""):
                    # Curated hubs: analyzer may not infer SPDX; still require recommendation.
                    if item.source not in ("clawhub", "awesome", "autoskills_map") or not analysis.recommended:
                        continue

                skill_md = await self.rewriter.rewrite(item, analysis)
                if proposed >= self._cfg.max_proposals_per_run:
                    break

                sid = await self.store.create_pending_proposal(
                    name=item.name[:200],
                    version=item.version[:80],
                    source_url=item.url[:2000],
                    license=analysis.license[:80],
                    copyright=(analysis.copyright or "")[:500],
                    score=effective,
                    content=skill_md,
                    tags=analysis.tags,
                )
                proposed += 1
                await self.notifier.notify_new_proposal(
                    name=item.name,
                    skill_id=sid,
                    score=effective,
                    source_url=item.url,
                )
            except Exception as e:
                logger.exception("process item %s: %s", item.name, e)

        try:
            async with aiosqlite.connect(db_module.db_path()) as db:
                await db.execute(
                    """
                    INSERT INTO hunt_logs
                    (source_type, items_found, items_passed, items_proposed, error)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ("skillhunter", len(items), len(items), proposed, None),
                )
                await db.commit()
        except Exception as e:
            logger.warning("hunt_logs insert failed: %s", e)

        return {"items": len(items), "proposed": proposed}
