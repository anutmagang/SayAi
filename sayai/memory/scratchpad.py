from __future__ import annotations

import asyncio
from typing import Any

from sayai.config import load_config


def _redis():
    try:
        import redis as redis_lib
    except ImportError:
        return None
    return redis_lib


class RedisScratchpad:
    """Working memory backed by Redis HASH per session (blueprint §7)."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        cfg = load_config()
        self._url = (cfg.memory.redis_url or "").strip()

    def _key(self) -> str:
        return f"sayai:scratch:{self.session_id}"

    def _client(self) -> Any | None:
        if not self._url:
            return None
        rlib = _redis()
        if not rlib:
            return None
        return rlib.Redis.from_url(self._url, decode_responses=True)

    async def hgetall(self) -> dict[str, str]:
        def _read() -> dict[str, str]:
            c = self._client()
            if not c:
                return {}
            raw = c.hgetall(self._key())
            return {str(k): str(v) for k, v in raw.items()}

        return await asyncio.to_thread(_read)

    async def hset(self, mapping: dict[str, str]) -> None:
        if not mapping:
            return

        def _write() -> None:
            c = self._client()
            if not c:
                return
            c.hset(self._key(), mapping=mapping)

        await asyncio.to_thread(_write)

    async def hset_one(self, key: str, value: str) -> None:
        await self.hset({key: value})

    async def hget(self, key: str) -> str | None:
        def _read() -> str | None:
            c = self._client()
            if not c:
                return None
            v = c.hget(self._key(), key)
            return str(v) if v is not None else None

        return await asyncio.to_thread(_read)
