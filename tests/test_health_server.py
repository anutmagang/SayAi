from sayai.server.health import _http_ok_json, _parse_request_line


def test_parse_request_line() -> None:
    raw = b"GET /health HTTP/1.1\r\nHost: x\r\n\r\n"
    assert _parse_request_line(raw) == "/health"


def test_http_ok_json_contains_service() -> None:
    body = _http_ok_json({"ok": True, "service": "sayai"})
    assert b"200 OK" in body
    assert b'"service":"sayai"' in body
