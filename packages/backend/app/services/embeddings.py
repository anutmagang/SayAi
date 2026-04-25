from __future__ import annotations

from typing import Any

from litellm import embedding as litellm_embedding


def embed_texts(*, model: str, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    resp: Any = litellm_embedding(model=model, input=texts)
    if isinstance(resp, dict):
        rows = resp.get("data") or []
        return [list(row["embedding"]) for row in rows]
    rows = getattr(resp, "data", []) or []
    return [list(row["embedding"]) for row in rows]
