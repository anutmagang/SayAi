from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import litellm

from sayai.llm.cost_log import maybe_log_litellm_usage
from sayai.llm.hooks import HookChain, _noop_post, _noop_pre
from sayai.llm.router import SmartRouter


def _dedupe_model_chain(primary: str, fallbacks: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in [primary, *fallbacks]:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


class LLMClient:
    def __init__(self, router: SmartRouter | None = None, hooks: HookChain | None = None):
        self.router = router or SmartRouter.from_settings()
        self.hooks = hooks or HookChain(pre=[_noop_pre], post=[_noop_post])

    async def _acompletion_with_fallbacks(
        self,
        *,
        messages: list[dict[str, Any]],
        task_type: str,
        budget: str,
        stream: bool,
        **kwargs: Any,
    ) -> Any:
        model = self.router.route(task_type=task_type, budget=budget)
        fallbacks = self.router.get_fallback(model)
        chain = _dedupe_model_chain(model, fallbacks)

        kw = dict(kwargs)
        kw.pop("fallbacks", None)
        kw["stream"] = stream

        last_err: BaseException | None = None
        for m in chain:
            try:
                return await litellm.acompletion(model=m, messages=messages, **kw)
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(
            f"All models in fallback chain failed for task_type={task_type!r}: {last_err!r}"
        ) from last_err

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        task_type: str = "default",
        budget: str = "normal",
        stream: bool = False,
        **kwargs: Any,
    ) -> str:
        messages = await self.hooks.before(messages, task_type=task_type)

        response = await self._acompletion_with_fallbacks(
            messages=messages,
            task_type=task_type,
            budget=budget,
            stream=stream,
            **kwargs,
        )

        if stream:
            chunks: list[str] = []
            async for part in response:
                choice = part.choices[0]
                delta = getattr(choice, "delta", None)
                if delta and getattr(delta, "content", None):
                    chunks.append(delta.content)
            text = "".join(chunks)
            return await self.hooks.after(text, response=None)

        await maybe_log_litellm_usage(response)
        text = response.choices[0].message.content or ""
        return await self.hooks.after(text, response=response)

    async def stream_text(
        self,
        messages: list[dict[str, Any]],
        *,
        task_type: str = "default",
        budget: str = "normal",
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        messages = await self.hooks.before(messages, task_type=task_type)

        response = await self._acompletion_with_fallbacks(
            messages=messages,
            task_type=task_type,
            budget=budget,
            stream=True,
            **kwargs,
        )

        assembled: list[str] = []
        async for part in response:
            choice = part.choices[0]
            delta = getattr(choice, "delta", None)
            if delta and getattr(delta, "content", None):
                assembled.append(delta.content)
                yield delta.content

        full = "".join(assembled)
        await self.hooks.after(full, response=None)
