from __future__ import annotations

from pathlib import Path

import pytest

from sayai.skillhunter.crawlers.autoskills_map_crawler import AutoskillsMapCrawler
from sayai.skillhunter.stack_profile import StackProfile, stack_relevance_boost


def test_stack_profile_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["litellm>=1.0", "click"]\n',
        encoding="utf-8",
    )
    p = StackProfile.detect(tmp_path)
    assert "litellm" in p.tokens
    assert "click" in p.tokens
    assert "litellm" in p.summary.lower()


def test_stack_relevance_boost() -> None:
    prof = StackProfile(tokens=frozenset({"react", "next"}), summary="react")
    b = stack_relevance_boost("foo", "Uses react patterns", "https://github.com/x/react-kit", prof)
    assert b > 0


def test_autoskills_map_parse_sample() -> None:
    c = AutoskillsMapCrawler(max_items=500)
    ts = '''
    skills: [
      "vercel-labs/agent-skills/react-best-practices",
      "https://bun.sh/docs",
      "foo/bar/baz-extra",
    ],
    '''
    keys = c._parse_repo_keys(ts)
    owners = {(o, r) for o, r, _ in keys}
    assert ("vercel-labs", "agent-skills") in owners
    assert ("foo", "bar") in owners


@pytest.mark.asyncio
async def test_skill_store_content_hash_and_approve_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sayai.db import database
    from sayai.db.database import init_db
    from sayai.db.skill_store import SkillStore, sha256_hex

    target = tmp_path / "h.db"
    monkeypatch.setattr(database, "db_path", lambda: target)
    from sayai.config import load_config

    load_config.cache_clear()
    await init_db()
    store = SkillStore()
    body = "---\nname: x\n---\nbody\n"
    sid = await store.create_pending_proposal(
        name="h",
        version="1",
        source_url="https://ex/h",
        license="MIT",
        copyright="",
        score=0.9,
        content=body,
        tags=[],
    )
    row = await store.get(sid)
    assert row and row["content_sha256"] == sha256_hex(body)

    with pytest.raises(ValueError, match="SHA-256"):
        await store.approve(sid, approved_by="a", content=body + "tampered")

    await store.approve(sid, approved_by="a", content=None)
    row2 = await store.get(sid)
    assert row2 and row2["status"] == "approved"

    block = await store.approved_skills_context_block(max_skills=5, max_total_chars=5000, per_skill_chars=2000)
    assert "Approved skill: h" in block
    assert "body" in block
