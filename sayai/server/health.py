from __future__ import annotations

import asyncio
import json
from typing import Any


def _http_ok_json(body: dict[str, Any]) -> bytes:
    raw = json.dumps(body, separators=(",", ":")).encode("utf-8")
    return (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        b"Connection: close\r\n"
        b"Content-Length: " + str(len(raw)).encode("ascii") + b"\r\n\r\n" + raw
    )


def _http_404() -> bytes:
    body = b'{"error":"not_found"}\n'
    return (
        b"HTTP/1.1 404 Not Found\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        b"Connection: close\r\n"
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
    )


def _parse_request_line(data: bytes) -> str:
    first = data.split(b"\r\n", 1)[0]
    parts = first.split()
    if len(parts) >= 2:
        return parts[1].decode("utf-8", errors="replace")
    return "/"


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        data = await reader.read(65536)
        path = _parse_request_line(data)
        if path in ("/health", "/healthz", "/"):
            writer.write(_http_ok_json({"ok": True, "service": "sayai"}))
        else:
            writer.write(_http_404())
        await writer.drain()
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def run_health_server(host: str, port: int) -> None:
    server = await asyncio.start_server(_handle_client, host=host, port=port)
    addrs = ", ".join(str(s.getsockname()) for s in server.sockets or [])
    async with server:
        await server.serve_forever()
