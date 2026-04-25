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
    reason="PostgreSQL not reachable; start `docker compose up -d postgres redis` then run tests.",
)

client = TestClient(app)


def _reset_tables() -> None:
    factory = get_session_factory()
    db = factory()
    try:
        truncate_sql = (
            "TRUNCATE TABLE workflow_run_steps, workflow_runs, workflows, "
            "rag_documents, rag_collections, skill_discovery_drafts, user_skill_settings, "
            "run_steps, chat_messages, runs, chat_sessions, api_keys, users CASCADE"
        )
        db.execute(text(truncate_sql))
        db.commit()
    finally:
        db.close()


def test_register_login_owner_then_me() -> None:
    _reset_tables()
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "longpassword1"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "owner"

    r2 = client.post("/api/v1/auth/login", json={"email": email, "password": "longpassword1"})
    assert r2.status_code == 200
    token = r2.json()["access_token"]

    r3 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json()["email"] == email


def test_api_key_auth() -> None:
    _reset_tables()
    email = f"keyuser-{uuid.uuid4().hex[:8]}@example.com"
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "longpassword1"},
    ).status_code == 200

    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "longpassword1"},
    ).json()["access_token"]

    r = client.post(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "ci", "scopes": ["*"]},
    )
    assert r.status_code == 200
    secret = r.json()["secret"]
    assert secret.startswith("sayai_")

    r2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {secret}"})
    assert r2.status_code == 200
    assert r2.json()["email"] == email
