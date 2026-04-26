from __future__ import annotations

from pathlib import Path

import aiosqlite

from sayai.config import load_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    version     TEXT,
    source_url  TEXT,
    license     TEXT,
    copyright   TEXT,
    content     TEXT,
    score       REAL,
    status      TEXT DEFAULT 'pending',
    tags        TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME,
    approved_by TEXT,
    approved_at DATETIME,
    reject_reason TEXT,
    store_revision INTEGER DEFAULT 1,
    content_sha256 TEXT
);

CREATE TABLE IF NOT EXISTS skill_sources (
    id          TEXT PRIMARY KEY,
    url         TEXT NOT NULL UNIQUE,
    type        TEXT,
    enabled     INTEGER DEFAULT 1,
    last_run    DATETIME,
    total_found INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS hunt_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT,
    items_found INTEGER,
    items_passed INTEGER,
    items_proposed INTEGER,
    error       TEXT
);

CREATE TABLE IF NOT EXISTS skill_usage (
    skill_id    TEXT,
    used_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    agent_type  TEXT,
    task_type   TEXT
);

CREATE TABLE IF NOT EXISTS skill_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    content TEXT,
    action TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


async def _migrate(db: aiosqlite.Connection) -> None:
    cur = await db.execute("PRAGMA table_info(skills)")
    rows = await cur.fetchall()
    col_names = {r[1] for r in rows}
    if "store_revision" not in col_names:
        try:
            await db.execute("ALTER TABLE skills ADD COLUMN store_revision INTEGER DEFAULT 1")
        except aiosqlite.OperationalError:
            pass
    if "content_sha256" not in col_names:
        try:
            await db.execute("ALTER TABLE skills ADD COLUMN content_sha256 TEXT")
        except aiosqlite.OperationalError:
            pass


def db_path() -> Path:
    load_config().data_dir.mkdir(parents=True, exist_ok=True)
    return load_config().data_dir / "sayai.db"


async def init_db() -> None:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.executescript(SCHEMA)
        await _migrate(db)
        await db.commit()
