from __future__ import annotations

import pytest

from app.skills.sandbox import parse_host_allowlist, validate_http_get_url


@pytest.mark.parametrize(
    ("url", "allow", "ok"),
    [
        ("https://example.com/path", None, True),
        ("http://127.0.0.1/", None, False),
        ("http://192.168.1.1/", None, False),
        ("http://[::1]/", None, False),
        ("http://metadata.google.internal/", None, False),
        ("ftp://example.com/", None, False),
        ("https://example.com/", frozenset({"other.com"}), False),
        ("https://example.com/", frozenset({"example.com"}), True),
    ],
)
def test_validate_http_get_url(url: str, allow: frozenset[str] | None, ok: bool) -> None:
    got, _reason = validate_http_get_url(url, host_allowlist=allow)
    assert got is ok


def test_parse_host_allowlist() -> None:
    assert parse_host_allowlist(None) is None
    assert parse_host_allowlist("") is None
    assert parse_host_allowlist("A.COM, b.org") == frozenset({"a.com", "b.org"})
