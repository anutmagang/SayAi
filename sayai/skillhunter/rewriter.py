from __future__ import annotations

from sayai.llm import LLMClient
from sayai.skillhunter.analyzer import AnalysisResult
from sayai.skillhunter.models import CrawlItem
from sayai.skillhunter.prompts import SKILLHUNTER_REWRITER_PROMPT, strip_md_fence


class SkillRewriter:
    def __init__(self, client: LLMClient | None = None):
        self.llm = client or LLMClient()

    async def rewrite(self, source: CrawlItem, analysis: AnalysisResult) -> str:
        user = (
            f"Source: {source.name} v{source.version}\n"
            f"URL: {source.url}\n"
            f"License (analyzer): {analysis.license}\n"
            f"Copyright: {analysis.copyright}\n"
            f"Summary: {analysis.summary}\n"
            f"Tags: {', '.join(analysis.tags)}\n"
            f"Description:\n{source.description}\n"
            f"README (truncated):\n{source.readme[:8000]}\n"
        )
        raw = await self.llm.complete(
            messages=[
                {"role": "system", "content": SKILLHUNTER_REWRITER_PROMPT},
                {"role": "user", "content": user},
            ],
            task_type="default",
            budget="normal",
        )
        return strip_md_fence(raw).strip()
