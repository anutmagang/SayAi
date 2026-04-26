from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from sayai.skillhunter.models import CrawlItem

logger = logging.getLogger(__name__)

DEFAULT_CONVEX_URL = "https://wry-manatee-359.convex.cloud"


class ClawHubConvexCrawler:
    """Public ClawHub skills via Convex HTTP API (list + optional README).

    Uses the same endpoints as clawhub.ai front-end. Configure ``convex_url`` if
    the deployment changes. Respect rate limits (``delay_sec``).
    """

    def __init__(
        self,
        *,
        convex_url: str = DEFAULT_CONVEX_URL,
        sort: str = "downloads",
        num_per_page: int = 25,
        max_pages: int = 3,
        fetch_readme: bool = True,
        delay_sec: float = 0.35,
        non_suspicious_only: bool = False,
    ) -> None:
        self.base = convex_url.rstrip("/")
        self.sort = sort
        self.num_per_page = max(1, min(num_per_page, 50))
        self.max_pages = max(1, max_pages)
        self.fetch_readme = fetch_readme
        self.delay_sec = delay_sec
        self.non_suspicious_only = non_suspicious_only

    async def _query(self, client: httpx.AsyncClient, path: str, args: list[dict[str, Any]]) -> dict[str, Any]:
        body = {"path": path, "format": "convex_encoded_json", "args": args}
        r = await client.post(
            f"{self.base}/api/query",
            json=body,
            headers={
                "content-type": "application/json",
                "convex-client": "npm-1.35.1",
            },
            timeout=60.0,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Convex query failed: {data!r}")
        return data.get("value") or {}

    async def _action(self, client: httpx.AsyncClient, path: str, args: list[dict[str, Any]]) -> dict[str, Any]:
        body = {"path": path, "format": "convex_encoded_json", "args": args}
        r = await client.post(
            f"{self.base}/api/action",
            json=body,
            headers={
                "content-type": "application/json",
                "convex-client": "npm-1.35.1",
            },
            timeout=90.0,
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Convex action failed: {data!r}")
        return data.get("value") or {}

    async def _readme_text(self, client: httpx.AsyncClient, version_id: str) -> str:
        if not version_id:
            return ""
        try:
            val = await self._action(client, "skills:getReadme", [{"versionId": version_id}])
            return str(val.get("text") or "")
        except Exception as e:
            logger.debug("getReadme %s: %s", version_id, e)
            return ""

    async def crawl(self) -> list[CrawlItem]:
        out: list[CrawlItem] = []
        cursor: str | None = None

        async with httpx.AsyncClient() as client:
            for page_idx in range(self.max_pages):
                args: dict[str, Any] = {
                    "dir": "desc",
                    "highlightedOnly": False,
                    "nonSuspiciousOnly": self.non_suspicious_only,
                    "numItems": self.num_per_page,
                    "sort": self.sort,
                }
                if cursor is not None:
                    args["cursor"] = cursor

                try:
                    val = await self._query(client, "skills:listPublicPageV4", [args])
                except Exception as e:
                    logger.warning("ClawHub listPublicPageV4 page %s: %s", page_idx, e)
                    break

                page = val.get("page") or []
                for row in page:
                    skill = row.get("skill") or {}
                    slug = str(skill.get("slug") or "").strip()
                    if not slug:
                        continue
                    owner = str(row.get("ownerHandle") or "").strip()
                    if not owner:
                        own = row.get("owner") or {}
                        owner = str(own.get("handle") or "").strip()
                    lv = row.get("latestVersion") or {}
                    version = str(lv.get("version") or "0")
                    vid = str(skill.get("latestVersionId") or lv.get("_id") or "").strip()
                    summary = str(skill.get("summary") or skill.get("displayName") or slug)
                    url = f"https://clawhub.ai/{owner}/{slug}" if owner else f"https://clawhub.ai/skills/{slug}"

                    readme = ""
                    if self.fetch_readme and vid:
                        readme = await self._readme_text(client, vid)
                        await asyncio.sleep(self.delay_sec)

                    stats = skill.get("stats") or {}
                    out.append(
                        CrawlItem(
                            name=f"clawhub__{owner}__{slug}".replace("/", "-"),
                            version=version,
                            url=url,
                            description=summary[:4000],
                            readme=readme[:50000],
                            license_hint="",
                            source="clawhub",
                            extra={
                                "slug": slug,
                                "owner": owner,
                                "version_id": vid,
                                "downloads": stats.get("downloads"),
                                "stars": stats.get("stars"),
                            },
                        )
                    )

                if not val.get("hasMore"):
                    break
                nxt = val.get("nextCursor")
                cursor = str(nxt) if nxt else None
                if not cursor:
                    break
                await asyncio.sleep(self.delay_sec)

        return out
