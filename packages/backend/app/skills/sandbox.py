"""URL and host checks for tool sandboxing (SSRF mitigation)."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

# Hostnames that must never be fetched by generic HTTP tools.
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost",
        "metadata.google.internal",
        "metadata.google",
        "kubernetes.default",
        "kubernetes.default.svc",
    }
)


def _parse_host_port(netloc: str) -> tuple[str, int | None]:
    raw = netloc.rsplit("@", 1)[-1]
    if raw.startswith("["):
        m = re.match(r"^\[([0-9a-fA-F:.]+)\](?::(\d+))?$", raw)
        if m:
            return m.group(1).lower(), int(m.group(2)) if m.group(2) else None
        return raw.lower().strip("[]"), None
    if ":" in raw and not raw.count(":") > 1:
        host, _, port_s = raw.rpartition(":")
        if port_s.isdigit():
            return host.lower(), int(port_s)
    return raw.lower(), None


def _ip_blocked(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_http_get_url(
    url: str,
    *,
    host_allowlist: frozenset[str] | None,
) -> tuple[bool, str]:
    """
    Return (ok, reason). When ok is False, reason is a short machine-readable code.
    """
    u = (url or "").strip()
    parsed = urlparse(u)
    if parsed.scheme not in ("http", "https"):
        return False, "only_http_https"
    if not parsed.netloc:
        return False, "missing_host"
    host, _port = _parse_host_port(parsed.netloc)
    if not host:
        return False, "missing_host"
    if host in _BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        return False, "blocked_hostname"
    if _ip_blocked(host):
        return False, "blocked_ip_host"
    if host_allowlist is not None and host not in host_allowlist:
        return False, "host_not_in_allowlist"
    return True, ""


def parse_host_allowlist(raw: str | None) -> frozenset[str] | None:
    if raw is None or not str(raw).strip():
        return None
    parts = {p.strip().lower() for p in str(raw).split(",") if p.strip()}
    return frozenset(parts) if parts else None
