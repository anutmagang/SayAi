from __future__ import annotations

import re
import logging
import httpx

from sayai.skillhunter.models import CrawlItem

logger = logging.getLogger(__name__)

# github.com/owner/repo — stop before next / (subpaths) or closing paren/quote/space
_GH_REPO = re.compile(
    r'https://github\.com/([\w.\-]+)/([\w.\-]+)(?:\.git)?(?=[/\s\)\]"\']|\?|#|$)',
    re.IGNORECASE,
)


def _normalize_github_url(owner: str, repo: str) -> str:
    return f"https://github.com/{owner}/{repo}".lower()


class AwesomeMarkdownCrawler:
    """Fetch curated awesome-list README(s) from raw GitHub and extract repo URLs."""

    def __init__(self, raw_readme_urls: list[str], *, max_repos: int = 40) -> None:
        self.urls = [u.strip() for u in raw_readme_urls if u.strip()]
        self.max_repos = max(1, max_repos)

    def _extract(self, text: str, *, max_pairs: int) -> list[tuple[str, str]]:
        seen: set[str] = set()
        pairs: list[tuple[str, str]] = []
        for m in _GH_REPO.finditer(text):
            owner, repo = m.group(1), m.group(2)
            if repo.lower().endswith(".git"):
                repo = repo[:-4]
            key = _normalize_github_url(owner, repo)
            if key in seen:
                continue
            if repo.lower() in ("issues", "pull", "discussions", "releases", "wiki", "blob", "tree"):
                continue
            if owner.lower() in ("topics", "sponsors", "apps", "settings"):
                continue
            seen.add(key)
            pairs.append((owner, repo))
            if len(pairs) >= max_pairs:
                break
        return pairs

    async def crawl(self) -> list[CrawlItem]:
        if not self.urls:
            return []

        out: list[CrawlItem] = []
        seen_url: set[str] = set()

        async with httpx.AsyncClient(timeout=60.0) as client:
            for raw_url in self.urls:
                try:
                    r = await client.get(raw_url)
                    r.raise_for_status()
                    text = r.text
                except Exception as e:
                    logger.warning("awesome fetch %s: %s", raw_url, e)
                    continue

                remaining = self.max_repos - len(out)
                if remaining <= 0:
                    return out
                for owner, repo in self._extract(text, max_pairs=remaining):
                    url = f"https://github.com/{owner}/{repo}"
                    if url.lower() in seen_url:
                        continue
                    seen_url.add(url.lower())
                    out.append(
                        CrawlItem(
                            name=f"{owner}__{repo}".replace("/", "-"),
                            version="main",
                            url=url,
                            description=f"From awesome list: {raw_url}",
                            readme="",
                            license_hint="",
                            source="awesome",
                            extra={"awesome_source": raw_url},
                        )
                    )
                    if len(out) >= self.max_repos:
                        return out

        return out
