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


class _FakeMsg:
    content = "workflow-ok"


class _FakeChoice:
    def __init__(self) -> None:
        self.message = _FakeMsg()


class _FakeResp:
    def __init__(self) -> None:
        self.choices = [_FakeChoice()]


def test_workflow_run_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_tables()

    def fake_completion(**kwargs: Any) -> _FakeResp:  # noqa: ARG001
        return _FakeResp()

    monkeypatch.setattr("app.services.workflow_executor.completion", fake_completion)

    email = f"wf-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "longpassword1"},
    )
    assert reg.status_code == 200
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "longpassword1"},
    ).json()["access_token"]

    definition = {
        "nodes": [
            {"id": "in1", "type": "wfInput", "data": {"label": "Input", "required": ["topic"]}},
            {
                "id": "llm1",
                "type": "wfLlm",
                "data": {
                    "label": "LLM",
                    "model": "gpt-4o-mini",
                    "prompt": "Say hi about {topic}",
                    "output_key": "summary",
                },
            },
            {
                "id": "out1",
                "type": "wfOutput",
                "data": {"label": "Output", "pick": "summary", "name": "result"},
            },
        ],
        "edges": [
            {"id": "e1", "source": "in1", "target": "llm1"},
            {"id": "e2", "source": "llm1", "target": "out1"},
        ],
    }

    wf = client.post(
        "/api/v1/workflows",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "demo", "definition": definition},
    )
    assert wf.status_code == 200, wf.text
    wf_id = wf.json()["id"]

    run = client.post(
        f"/api/v1/workflows/{wf_id}/runs",
        headers={"Authorization": f"Bearer {token}"},
        json={"inputs": {"topic": "cats"}, "await_completion": True},
    )
    assert run.status_code == 200, run.text
    run_id = run.json()["id"]
    assert run.json()["status"] == "completed"

    trace = client.get(
        f"/api/v1/workflow-runs/{run_id}/trace",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert trace.status_code == 200
    assert len(trace.json()) >= 2
