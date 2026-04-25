from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.db_util import postgres_available
from tests.test_auth import _reset_tables

pytestmark = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL not reachable; start `docker compose up -d postgres redis` then run tests.",
)

client = TestClient(app)


class _FakeUsage:
    prompt_tokens = 3
    completion_tokens = 5


class _FakeMsgObj:
    def __init__(self, d: dict[str, Any]) -> None:
        self._d = d

    def model_dump(self, *, exclude_none: bool = True) -> dict[str, Any]:
        _ = exclude_none
        return self._d


class _FakeChoice:
    def __init__(self, message: dict[str, Any]) -> None:
        self.message = _FakeMsgObj(message)


class _FakeResp:
    def __init__(self, message: dict[str, Any]) -> None:
        self.choices = [_FakeChoice(message)]
        self.usage = _FakeUsage()


def test_run_chat_await_completion_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_tables()

    calls: dict[str, int] = {"n": 0}

    def fake_completion(**kwargs: Any) -> _FakeResp:  # noqa: ARG001
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "sayai_echo", "arguments": '{"message":"hi"}'},
                        }
                    ],
                }
            )
        return _FakeResp({"role": "assistant", "content": "done"})

    monkeypatch.setattr("app.services.run_worker.completion", fake_completion)

    email = f"run-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "longpassword1"},
    )
    assert reg.status_code == 200
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "longpassword1"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mode": "chat",
            "message": "hello",
            "await_completion": True,
            "model": "gpt-4o-mini",
            "skill_allowlist": ["sayai.echo"],
        },
    )
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]

    trace = client.get(f"/api/v1/runs/{run_id}/trace", headers={"Authorization": f"Bearer {token}"})
    assert trace.status_code == 200
    steps = trace.json()
    assert len(steps) >= 2
    kinds = [s["step_type"] for s in steps]
    assert "llm" in kinds
    assert "tool" in kinds
