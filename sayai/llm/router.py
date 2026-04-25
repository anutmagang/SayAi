from __future__ import annotations

from dataclasses import dataclass, field

from sayai.config import load_config


@dataclass
class SmartRouter:
    """Maps task_type + budget to a LiteLLM model id; merges YAML routing + fallbacks."""

    _routing: dict[str, str] = field(default_factory=dict)
    _fallback_chains: dict[str, list[str]] = field(default_factory=dict)
    _default_model: str = ""

    @classmethod
    def from_settings(cls) -> SmartRouter:
        s = load_config()
        routing = {
            "planning": s.llm.routing.get("planning", s.llm.default_model),
            "coding": s.llm.routing.get("coding", s.llm.default_model),
            "reviewing": s.llm.routing.get("reviewing", s.llm.default_model),
            "searching": s.llm.routing.get("searching", s.llm.default_model),
            "testing": s.llm.routing.get("testing", s.llm.default_model),
            "cheap": s.llm.routing.get("cheap", s.llm.default_model),
            "default": s.llm.routing.get("default", s.llm.default_model),
        }
        return cls(
            _routing=routing,
            _fallback_chains=dict(s.llm.fallback_chains),
            _default_model=s.llm.default_model,
        )

    def route(self, task_type: str = "default", budget: str = "normal") -> str:
        if budget == "cheap":
            return self._routing.get("cheap", self._default_model)
        return self._routing.get(task_type, self._routing.get("default", self._default_model))

    def get_fallback(self, model: str) -> list[str]:
        return list(self._fallback_chains.get(model, []))
