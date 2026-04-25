from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sayai.llm import LLMClient
from sayai.skillhunter.models import CrawlItem
from sayai.skillhunter.prompts import SKILLHUNTER_ANALYZER_PROMPT, strip_json_fence


@dataclass
class AnalysisResult:
    score: float
    license: str
    copyright: str
    is_duplicate: bool
    safety_ok: bool
    tags: list[str]
    summary: str
    rejection_reason: str | None
    recommended: bool


class SkillAnalyzer:
    def __init__(self, client: LLMClient | None = None):
        self.llm = client or LLMClient()

    def _heuristic_safety(self, item: CrawlItem) -> bool:
        blob = (item.url + item.description + item.readme).lower()
        bad = (
            "cryptominer",
            "wallet.dat",
            "powershell -enc",
            "curl | bash",
            "pastebin.com/raw",
            "bit.ly/",
        )
        return not any(b in blob for b in bad)

    async def analyze(self, item: CrawlItem) -> AnalysisResult:
        if not self._heuristic_safety(item):
            return AnalysisResult(
                score=0.0,
                license="unknown",
                copyright="",
                is_duplicate=False,
                safety_ok=False,
                tags=[],
                summary="blocked by safety heuristic",
                rejection_reason="safety_heuristic",
                recommended=False,
            )

        user = (
            f"Name: {item.name}\nVersion: {item.version}\nURL: {item.url}\n"
            f"Source: {item.source}\nLicense hint: {item.license_hint}\n"
            f"Description: {item.description}\nREADME excerpt:\n{item.readme[:6000]}\n"
        )
        raw = await self.llm.complete(
            messages=[
                {"role": "system", "content": SKILLHUNTER_ANALYZER_PROMPT},
                {"role": "user", "content": user},
            ],
            task_type="default",
            budget="cheap",
        )
        try:
            data = json.loads(strip_json_fence(raw))
        except json.JSONDecodeError:
            return AnalysisResult(
                score=0.4,
                license=item.license_hint or "unknown",
                copyright="",
                is_duplicate=False,
                safety_ok=True,
                tags=[],
                summary=item.description[:200],
                rejection_reason="analyzer_json_parse",
                recommended=False,
            )
        return AnalysisResult(
            score=float(data.get("score", 0)),
            license=str(data.get("license", "unknown")),
            copyright=str(data.get("copyright", "")),
            is_duplicate=bool(data.get("is_duplicate", False)),
            safety_ok=bool(data.get("safety_ok", True)),
            tags=[str(t) for t in (data.get("tags") or []) if t][:24],
            summary=str(data.get("summary", "")),
            rejection_reason=data.get("rejection_reason"),
            recommended=bool(data.get("recommended", True)),
        )
