from __future__ import annotations

from typing import Any

import httpx

from sayai.skillhunter.models import CrawlItem


class MCPRegistryCrawler:
    """Fetch MCP server listings from a registry JSON endpoint."""

    def __init__(self, registry_url: str, *, max_items: int = 20):
        self.registry_url = registry_url.rstrip("/")
        self.max_items = max_items

    def _normalize(self, raw: Any) -> list[CrawlItem]:
        items: list[dict[str, Any]] = []
        if isinstance(raw, list):
            items = [x for x in raw if isinstance(x, dict)]
        elif isinstance(raw, dict):
            for key in ("servers", "items", "data", "results"):
                v = raw.get(key)
                if isinstance(v, list):
                    items = [x for x in v if isinstance(x, dict)]
                    break
        out: list[CrawlItem] = []
        for it in items[: self.max_items]:
            name = str(it.get("name") or it.get("title") or it.get("id") or "mcp-server")
            ver = str(it.get("version") or it.get("latest") or "0")
            url = str(it.get("repository") or it.get("url") or it.get("homepage") or "")
            if not url:
                continue
            desc = str(it.get("description") or it.get("summary") or "")
            lic = str(it.get("license") or it.get("license_spdx") or "unknown")
            out.append(
                CrawlItem(
                    name=name.replace("/", "-")[:120],
                    version=ver,
                    url=url,
                    description=desc,
                    readme=str(it.get("readme") or "")[:4000],
                    license_hint=lic,
                    source="mcp",
                    extra={"raw_keys": list(it.keys())[:20]},
                )
            )
        return out

    async def crawl(self) -> list[CrawlItem]:
        if not self.registry_url:
            return []
        try:
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                r = await client.get(
                    self.registry_url,
                    headers={"User-Agent": "SayAi-SkillHunter/0.4", "Accept": "application/json"},
                )
                if r.status_code != 200:
                    return []
                raw = r.json()
        except Exception:
            return []
        return self._normalize(raw)
