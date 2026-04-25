from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.skills.sandbox import parse_host_allowlist, validate_http_get_url


def echo_handler(args: dict[str, Any]) -> dict[str, Any]:
    msg = str(args.get("message", ""))
    return {"echo": msg}


def http_get_handler(args: dict[str, Any]) -> dict[str, Any]:
    url = str(args.get("url", "")).strip()
    settings = get_settings()
    allow = parse_host_allowlist(settings.skill_http_host_allowlist)
    ok, reason = validate_http_get_url(url, host_allowlist=allow)
    if not ok:
        return {"error": f"url_blocked:{reason}"}
    try:
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        text = resp.text
        if len(text) > 8000:
            text = text[:8000] + "…"
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "text": text,
        }
    except Exception as exc:  # pragma: no cover - network dependent
        return {"error": str(exc)}


def noop_handler(args: dict[str, Any]) -> dict[str, Any]:
    _ = args
    return {}


BUILTIN: list[dict[str, Any]] = [
    {
        "id": "sayai.echo",
        "description": "Echo back a short string (useful for sanity checks).",
        "parameters": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
        "handler": echo_handler,
    },
    {
        "id": "sayai.http_get",
        "description": "Fetch a public HTTP(S) URL and return status, headers, and body text.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        "handler": http_get_handler,
    },
    {
        "id": "sayai.memory_len",
        "description": "Return how many messages are currently in the session context buffer.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": noop_handler,
    },
]
