from __future__ import annotations

from typing import Any

import httpx

from sayai.config import load_config


class MCPBridge:
    """Forward tool calls to configured HTTP MCP-style servers (blueprint §8)."""

    def __init__(self) -> None:
        cfg = load_config()
        self._servers: dict[str, str] = {}
        for row in cfg.mcp.servers:
            name = str(row.get("name", "")).strip()
            url = str(row.get("url", "")).strip().rstrip("/")
            if name and url:
                self._servers[name] = url

    def list_servers(self) -> list[str]:
        return sorted(self._servers.keys())

    async def call(self, server: str, tool: str, arguments: dict[str, Any] | None = None) -> str:
        base = self._servers.get(server)
        if not base:
            return f"Error: MCP server '{server}' not configured. Known: {self.list_servers()}"
        url = f"{base}/tools/{tool}"
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(url, json=arguments or {})
                return r.text[:50_000] or f"(empty response status={r.status_code})"
        except Exception as e:
            return f"Error: MCP call failed: {e}"
