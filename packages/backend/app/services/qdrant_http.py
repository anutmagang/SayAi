from __future__ import annotations

from typing import Any

import httpx


class QdrantHttp:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def close(self) -> None:
        self.client.close()

    def collection_exists(self, name: str) -> bool:
        r = self.client.get(f"{self.base}/collections/{name}")
        return r.status_code == 200

    def create_collection(self, name: str, *, vector_size: int) -> None:
        if self.collection_exists(name):
            return
        payload = {"vectors": {"size": vector_size, "distance": "Cosine"}}
        r = self.client.put(f"{self.base}/collections/{name}", json=payload)
        r.raise_for_status()

    def delete_collection(self, name: str) -> None:
        r = self.client.delete(f"{self.base}/collections/{name}")
        if r.status_code not in (200, 404):
            r.raise_for_status()

    def upsert_points(self, name: str, points: list[dict[str, Any]]) -> None:
        r = self.client.put(
            f"{self.base}/collections/{name}/points",
            params={"wait": "true"},
            json={"points": points},
        )
        r.raise_for_status()

    def search(
        self,
        name: str,
        *,
        vector: list[float],
        limit: int,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {"vector": vector, "limit": limit, "with_payload": True}
        if score_threshold is not None:
            body["score_threshold"] = score_threshold
        r = self.client.post(f"{self.base}/collections/{name}/points/search", json=body)
        r.raise_for_status()
        data = r.json()
        return list(data.get("result") or [])
