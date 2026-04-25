from __future__ import annotations

from typing import Any, Protocol


class PreHook(Protocol):
    async def __call__(
        self, messages: list[dict[str, Any]], *, task_type: str
    ) -> list[dict[str, Any]]: ...


class PostHook(Protocol):
    async def __call__(self, text: str, *, response: Any | None = None) -> str: ...


class HookChain:
    def __init__(self, pre: list[PreHook] | None = None, post: list[PostHook] | None = None):
        self._pre = pre or []
        self._post = post or []

    async def before(self, messages: list[dict[str, Any]], *, task_type: str) -> list[dict[str, Any]]:
        m = messages
        for h in self._pre:
            m = await h(m, task_type=task_type)
        return m

    async def after(self, text: str, *, response: Any | None = None) -> str:
        t = text
        for h in self._post:
            t = await h(t, response=response)
        return t


async def _noop_pre(
    messages: list[dict[str, Any]], *, task_type: str
) -> list[dict[str, Any]]:
    return messages


async def _noop_post(text: str, *, response: Any | None = None) -> str:
    return text
