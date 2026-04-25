from __future__ import annotations

from typing import Any

from sayai.llm import LLMClient

AGGREGATOR_SYSTEM = """You are the SayAi Aggregator. Merge outputs from multiple specialist agents
into one coherent answer for the user. Preserve important commands, file paths, and errors.
Be concise; use markdown sections when helpful."""


class Aggregator:
    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()

    async def merge(self, user_task: str, results: dict[str, Any]) -> str:
        lines: list[str] = []
        for tid, body in results.items():
            lines.append(f"## Task `{tid}`\n{str(body).strip()}\n")
        bundle = "\n".join(lines)
        return await self.client.complete(
            messages=[
                {"role": "system", "content": AGGREGATOR_SYSTEM},
                {
                    "role": "user",
                    "content": f"Original request:\n{user_task}\n\n--- Agent outputs ---\n{bundle}",
                },
            ],
            task_type="planning",
            budget="normal",
        )
