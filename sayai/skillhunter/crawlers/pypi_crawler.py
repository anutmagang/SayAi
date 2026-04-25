from __future__ import annotations

import re
from typing import Any

import httpx

from sayai.skillhunter.models import CrawlItem


class PyPICrawler:
    """Discover packages via PyPI search HTML + project JSON metadata."""

    def __init__(self, query: str, *, max_packages: int = 12):
        self.query = query
        self.max_packages = max_packages

    async def _project_json(self, client: httpx.AsyncClient, name: str) -> dict[str, Any] | None:
        r = await client.get(f"https://pypi.org/pypi/{name}/json", timeout=30.0)
        if r.status_code != 200:
            return None
        return r.json()

    async def crawl(self) -> list[CrawlItem]:
        search_url = "https://pypi.org/search"
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
            r = await client.get(search_url, params={"q": self.query})
            if r.status_code != 200:
                return []
            html = r.text

        # Package names from search result links
        names = list(
            dict.fromkeys(
                m.group(1)
                for m in re.finditer(r'href="/project/([^/]+)/"', html)
                if m.group(1) and m.group(1) != "help"
            )
        )[: self.max_packages]

        out: list[CrawlItem] = []
        async with httpx.AsyncClient(timeout=45.0) as client:
            for name in names:
                pj = await self._project_json(client, name)
                if not pj:
                    continue
                info = pj.get("info") or {}
                desc = str(info.get("summary") or "")
                lic = str(info.get("license") or "unknown")
                ver = str(info.get("version") or "0")
                urls = info.get("project_urls") or {}
                home = urls.get("Homepage") or urls.get("Source") or f"https://pypi.org/project/{name}/"
                readme = ""
                try:
                    rd = info.get("description") or ""
                    readme = str(rd)[:8000]
                except Exception:
                    pass
                out.append(
                    CrawlItem(
                        name=name,
                        version=ver,
                        url=str(home),
                        description=desc,
                        readme=readme,
                        license_hint=lic,
                        source="pypi",
                        extra={"pypi": name},
                    )
                )
        return out
