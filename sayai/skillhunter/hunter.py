from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiosqlite

from sayai.config import load_config
from sayai.db import database as db_module
from sayai.db.skill_store import SkillStore
from sayai.skillhunter.analyzer import SkillAnalyzer
from sayai.skillhunter.crawlers import GitHubCrawler, MCPRegistryCrawler, PyPICrawler
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
        return [
            GitHubCrawler(self._cfg.github_query, per_page=15),
            PyPICrawler(self._cfg.pypi_query, max_packages=12),
            MCPRegistryCrawler(self._cfg.mcp_registry_url, max_items=18),
        ]

    async def hunt(self) -> dict[str, int]:
        if not self._cfg.enabled:
            logger.info("SkillHunter disabled in config")
            return {"items": 0, "proposed": 0}

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
                analysis = await self.analyzer.analyze(item)
                if analysis.is_duplicate:
                    continue
                if analysis.score < self._cfg.min_score:
                    continue
                if not analysis.safety_ok or not analysis.recommended:
                    continue
                lic = (analysis.license or "").lower()
                if lic in ("unknown", "proprietary", "no-license", ""):
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
                    score=analysis.score,
                    content=skill_md,
                    tags=analysis.tags,
                )
                proposed += 1
                await self.notifier.notify_new_proposal(
                    name=item.name,
                    skill_id=sid,
                    score=analysis.score,
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
