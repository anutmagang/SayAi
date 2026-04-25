from __future__ import annotations

import pytest

from sayai.config import load_config


@pytest.mark.asyncio
async def test_skill_store_proposal_approve(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sayai.db import database
    from sayai.db.database import init_db
    from sayai.db.skill_store import SkillStore

    target = tmp_path / "skill.db"
    monkeypatch.setattr(database, "db_path", lambda: target)
    load_config.cache_clear()
    await init_db()

    store = SkillStore()
    sid = await store.create_pending_proposal(
        name="demo-skill",
        version="1.0.0",
        source_url="https://example.com/pkg",
        license="MIT",
        copyright="2026 Demo",
        score=0.85,
        content="---\nname: demo\n---\n# X\n",
        tags=["demo", "test"],
    )
    assert await store.exists_source_url("https://example.com/pkg")
    row = await store.get(sid)
    assert row and row["status"] == "pending"

    await store.approve(sid, approved_by="tester")
    row2 = await store.get(sid)
    assert row2 and row2["status"] == "approved"
    vers = await store.list_versions(sid)
    assert len(vers) >= 2


@pytest.mark.asyncio
async def test_skill_store_reject(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sayai.db import database
    from sayai.db.database import init_db
    from sayai.db.skill_store import SkillStore

    target = tmp_path / "skill2.db"
    monkeypatch.setattr(database, "db_path", lambda: target)
    load_config.cache_clear()
    await init_db()
    store = SkillStore()
    sid = await store.create_pending_proposal(
        name="bad",
        version="0.0.1",
        source_url="https://example.com/bad",
        license="MIT",
        copyright="",
        score=0.5,
        content="x",
        tags=[],
    )
    await store.reject(sid, "license unclear", by="tester")
    row = await store.get(sid)
    assert row and row["status"] == "rejected"
