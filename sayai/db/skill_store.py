from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from sayai.db import database as db_module


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_hex(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class SkillStore:
    """Skill proposals, approvals, and version history (blueprint §13)."""

    def __init__(self, path: Any | None = None):
        self._path = Path(path) if path is not None else db_module.db_path()

    async def exists_source_url(self, url: str) -> bool:
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "SELECT 1 FROM skills WHERE source_url = ? LIMIT 1",
                (url,),
            )
            row = await cur.fetchone()
            return row is not None

    async def create_pending_proposal(
        self,
        *,
        name: str,
        version: str,
        source_url: str,
        license: str,
        copyright: str,
        score: float,
        content: str,
        tags: list[str],
    ) -> str:
        sid = str(uuid.uuid4())
        tags_json = json.dumps(tags, ensure_ascii=False)
        now = _utc_now()
        digest = sha256_hex(content)
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT INTO skills (
                    id, name, version, source_url, license, copyright,
                    content, score, status, tags, created_at, updated_at, store_revision,
                    content_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, 1, ?)
                """,
                (
                    sid,
                    name,
                    version,
                    source_url,
                    license,
                    copyright,
                    content,
                    score,
                    tags_json,
                    now,
                    now,
                    digest,
                ),
            )
            await db.execute(
                """
                INSERT INTO skill_versions (skill_id, revision, content, action, created_at)
                VALUES (?, 1, ?, 'proposed', ?)
                """,
                (sid, content, now),
            )
            await db.commit()
        return sid

    async def list_by_status(self, status: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT * FROM skills WHERE status = ? ORDER BY score DESC, created_at DESC
                """,
                (status,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def approved_skills_context_block(
        self,
        *,
        max_skills: int = 12,
        max_total_chars: int = 12_000,
        per_skill_chars: int = 4000,
    ) -> str:
        """Concatenate approved SKILL bodies for injection into agent system prompts."""
        rows = await self.list_by_status("approved")
        if not rows:
            return ""
        header = (
            "---\n"
            "Approved SayAi skills (from SQLite store). Follow when relevant to the task; "
            "do not override tool-safety rules.\n"
            "---\n"
        )
        parts: list[str] = [header]
        used = len(header)
        for row in rows[:max_skills]:
            name = str(row.get("name") or "skill").strip() or "skill"
            content = str(row.get("content") or "").strip()
            if not content:
                continue
            body = content[:per_skill_chars]
            if len(content) > per_skill_chars:
                body += "\n…[skill truncated]\n"
            section = f"\n### Approved skill: {name}\n{body}\n"
            if used + len(section) > max_total_chars:
                break
            parts.append(section)
            used += len(section)
        if len(parts) <= 1:
            return ""
        return "".join(parts)

    async def get(self, skill_id: str) -> dict[str, Any] | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
            row = await cur.fetchone()
            return dict(row) if row else None

    async def list_versions(self, skill_id: str) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT * FROM skill_versions WHERE skill_id = ?
                ORDER BY revision DESC, id DESC
                """,
                (skill_id,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def update_pending_content(self, skill_id: str, content: str) -> None:
        now = _utc_now()
        async with aiosqlite.connect(self._path) as db:
            digest = sha256_hex(content)
            await db.execute(
                """
                UPDATE skills SET content = ?, updated_at = ?, content_sha256 = ?
                WHERE id = ? AND status = 'pending'
                """,
                (content, now, digest, skill_id),
            )
            await db.commit()

    async def approve(
        self,
        skill_id: str,
        *,
        approved_by: str,
        content: str | None = None,
    ) -> None:
        now = _utc_now()
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute(
                """
                SELECT content, content_sha256, COALESCE(store_revision, 1) AS sr, status
                FROM skills WHERE id = ?
                """,
                (skill_id,),
            )
            row = await cur.fetchone()
            if not row:
                raise KeyError(skill_id)
            if row["status"] != "pending":
                raise ValueError("skill not in pending state")
            new_content = content if content is not None else str(row["content"])
            stored_hash = row["content_sha256"]
            if stored_hash:
                if sha256_hex(new_content) != str(stored_hash):
                    raise ValueError(
                        "Approved content SHA-256 does not match pending proposal "
                        "(content changed or corrupted)."
                    )
            new_rev = int(row["sr"]) + 1
            digest_final = sha256_hex(new_content)
            await db.execute(
                """
                UPDATE skills SET status = 'approved', approved_by = ?, approved_at = ?,
                updated_at = ?, content = ?, store_revision = ?, content_sha256 = ?
                WHERE id = ? AND status = 'pending'
                """,
                (approved_by, now, now, new_content, new_rev, digest_final, skill_id),
            )
            await db.execute(
                """
                INSERT INTO skill_versions (skill_id, revision, content, action, created_at)
                VALUES (?, ?, ?, 'approved', ?)
                """,
                (skill_id, new_rev, new_content, now),
            )
            await db.commit()

    async def reject(self, skill_id: str, reason: str, *, by: str = "admin") -> None:
        now = _utc_now()
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT status FROM skills WHERE id = ?", (skill_id,))
            row = await cur.fetchone()
            if not row or row["status"] != "pending":
                raise ValueError("skill not pending or missing")
            await db.execute(
                """
                UPDATE skills SET status = 'rejected', reject_reason = ?, updated_at = ?,
                approved_by = ?
                WHERE id = ? AND status = 'pending'
                """,
                (reason, now, by, skill_id),
            )
            await db.execute(
                """
                INSERT INTO skill_versions (skill_id, revision, content, action, created_at)
                VALUES (?, 0, ?, 'rejected', ?)
                """,
                (skill_id, reason, now),
            )
            await db.commit()
