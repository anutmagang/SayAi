from __future__ import annotations

from collections import deque
from typing import Any

from sayai.config import load_config


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    return sum(len(m.get("content", "")) for m in messages) // 4


class ContextManager:
    """Short-term per-agent sliding window (blueprint Layer 4)."""

    def __init__(self, agent_id: str, *, max_tokens: int | None = None):
        self.agent_id = agent_id
        cfg = load_config()
        self.max_tokens = max_tokens if max_tokens is not None else cfg.memory.short_term_tokens
        self.messages: deque[dict[str, Any]] = deque()

    def clear(self) -> None:
        self.messages.clear()

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self._trim_if_needed()

    def _trim_if_needed(self) -> None:
        while len(self.messages) > 1 and _estimate_tokens(list(self.messages)) > self.max_tokens:
            if self.messages[0].get("role") == "system":
                rest = list(self.messages)
                if len(rest) > 20:
                    dropped = rest[1:21]
                    kept = [rest[0]] + rest[21:]
                    summary = f"[Context trimmed: dropped {len(dropped)} older turns for agent {self.agent_id}]"
                    kept.insert(1, {"role": "user", "content": summary})
                    self.messages = deque(kept)
                else:
                    rest.pop(1)
                    self.messages = deque(rest)
            else:
                self.messages.popleft()

    def get_messages(self) -> list[dict[str, Any]]:
        return list(self.messages)
