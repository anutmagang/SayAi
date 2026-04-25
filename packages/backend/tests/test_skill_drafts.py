from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_session_factory
from app.main import app
from tests.db_util import postgres_available

pytestmark = pytest.mark.skipif(
    not postgres_available(),
    reason="PostgreSQL not reachable",
)

client = TestClient(app)


def _reset_tables() -> None:
    factory = get_session_factory()
    db = factory()
    try:
        db.execute(
            text(
                "TRUNCATE TABLE workflow_run_steps, workflow_runs, workflows, "
                "rag_documents, rag_collections, skill_discovery_drafts, user_skill_settings, "
                "run_steps, chat_messages, runs, chat_sessions, api_keys, users CASCADE",
            ),
        )
        db.commit()
    finally:
        db.close()


def test_skill_drafts_crud() -> None:
    _reset_tables()
    email = f"drafter-{uuid.uuid4().hex[:8]}@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "longpassword1"},
    ).status_code == 200
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "longpassword1"},
    ).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/api/v1/skill-drafts",
        headers=h,
        json={"title": "My skill idea", "body": {"proposed_id": "acme.widget", "notes": "x"}},
    )
    assert r.status_code == 200
    did = r.json()["id"]

    r2 = client.get("/api/v1/skill-drafts", headers=h)
    assert r2.status_code == 200
    assert len(r2.json()) == 1

    r3 = client.patch(
        f"/api/v1/skill-drafts/{did}",
        headers=h,
        json={"status": "submitted"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "submitted"

    r4 = client.delete(f"/api/v1/skill-drafts/{did}", headers=h)
    assert r4.status_code == 204
