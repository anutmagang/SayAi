from pathlib import Path

import pytest

from sayai.config import load_config
from sayai.llm import SmartRouter


def test_load_config() -> None:
    s = load_config()
    assert s.sayai.mode == "local"
    assert s.agents.max_iterations >= 1


def test_router() -> None:
    r = SmartRouter.from_settings()
    m = r.route("coding", budget="normal")
    assert isinstance(m, str) and len(m) > 0


@pytest.mark.asyncio
async def test_init_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sayai.db import database

    target = tmp_path / "sayai_test.db"

    monkeypatch.setattr(database, "db_path", lambda: target)
    await database.init_db()
    assert target.is_file()
