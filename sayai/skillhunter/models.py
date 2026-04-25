from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CrawlItem:
    """Normalized candidate from any crawler."""

    name: str
    version: str
    url: str
    description: str
    readme: str = ""
    license_hint: str = ""
    source: str = ""  # github | pypi | mcp
    extra: dict[str, object] = field(default_factory=dict)
