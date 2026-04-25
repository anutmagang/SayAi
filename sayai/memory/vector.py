from __future__ import annotations

import uuid
from typing import Any

import litellm

from sayai.config import load_config


class VectorMemory:
    """Long-term memory via Qdrant (blueprint §7). Disabled when qdrant_enabled is false."""

    def __init__(self) -> None:
        self._client: Any = None
        self._collection_ready: bool = False
        self._last_error: str | None = None

    def _client_or_none(self) -> Any:
        cfg = load_config()
        if not cfg.memory.qdrant_enabled:
            return None
        if self._client is not None:
            return self._client
        try:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(url=cfg.memory.qdrant_url, timeout=30)
            self._last_error = None
        except Exception as e:
            self._last_error = str(e)
            self._client = None
        return self._client

    def _ensure_collection(self) -> bool:
        cfg = load_config()
        client = self._client_or_none()
        if not client:
            return False
        if self._collection_ready:
            return True
        name = cfg.memory.qdrant_collection
        dim = cfg.memory.embedding_dimensions
        try:
            from qdrant_client.models import Distance, VectorParams

            cols = [c.name for c in client.get_collections().collections]
            if name not in cols:
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                )
            self._collection_ready = True
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    async def embed(self, text: str) -> list[float]:
        cfg = load_config()
        resp = await litellm.aembedding(model=cfg.memory.embedding_model, input=text)
        if hasattr(resp, "model_dump"):
            data = resp.model_dump()
        elif isinstance(resp, dict):
            data = resp
        else:
            data = dict(resp)
        vec = list(data["data"][0]["embedding"])
        return vec

    async def upsert(
        self,
        content: str,
        *,
        path: str = "",
        source: str = "index",
        extra: dict[str, Any] | None = None,
    ) -> str:
        cfg = load_config()
        client = self._client_or_none()
        if not client or not self._ensure_collection():
            return f"(vector memory disabled: {self._last_error or 'qdrant off'})"
        vec = await self.embed(content[:80_000])
        from qdrant_client.models import PointStruct

        payload = {
            "content": content[:50_000],
            "path": path,
            "source": source,
            **(extra or {}),
        }
        pid = str(uuid.uuid4())
        client.upsert(
            collection_name=cfg.memory.qdrant_collection,
            points=[PointStruct(id=pid, vector=vec, payload=payload)],
        )
        return f"OK upsert id={pid}"

    async def search(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        cfg = load_config()
        client = self._client_or_none()
        if not client or not self._ensure_collection():
            return []
        vec = await self.embed(query[:20_000])
        hits = client.search(
            collection_name=cfg.memory.qdrant_collection,
            query_vector=vec,
            limit=top_k,
        )
        out: list[dict[str, Any]] = []
        for r in hits:
            pl = r.payload or {}
            out.append(
                {
                    "score": r.score,
                    "content": pl.get("content", ""),
                    "path": pl.get("path", ""),
                    "source": pl.get("source", ""),
                }
            )
        return out


_vector_singleton: VectorMemory | None = None


def get_vector_memory() -> VectorMemory:
    global _vector_singleton
    if _vector_singleton is None:
        _vector_singleton = VectorMemory()
    return _vector_singleton
