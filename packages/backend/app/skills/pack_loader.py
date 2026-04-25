"""Load marketplace-style skill packs from disk (manifest-only, safe handler reuse)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.skills.builtin import BUILTIN
from app.skills.records import SkillRecord

_ID_RE = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pack_dirs() -> list[Path]:
    dirs: list[Path] = []
    builtin_packs = _backend_root() / "skill_packs"
    if builtin_packs.is_dir():
        dirs.append(builtin_packs)
    raw = get_settings().skill_packs_extra_dirs
    if raw:
        for part in str(raw).split(","):
            p = Path(part.strip()).expanduser()
            if p.is_dir():
                dirs.append(p)
    return dirs


def _builtin_index() -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in BUILTIN}


def load_pack_skill_records() -> list[SkillRecord]:
    """Return extra skills declared by pack manifests (extend built-ins only)."""
    builtin = _builtin_index()
    seen_ids = set(builtin.keys())
    out: list[SkillRecord] = []

    for base in _pack_dirs():
        for manifest_path in sorted(base.glob("*/manifest.json")):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            pack_id = str(data.get("pack_id") or manifest_path.parent.name)
            for spec in data.get("skills") or []:
                sid = str(spec.get("id") or "")
                ext = str(spec.get("extends_skill_id") or "")
                if not _ID_RE.match(sid) or sid in seen_ids:
                    continue
                if ext not in builtin:
                    continue
                desc = str(spec.get("description") or builtin[ext]["description"])
                params = spec.get("parameters")
                if not isinstance(params, dict):
                    params = builtin[ext]["parameters"]
                handler = builtin[ext]["handler"]
                out.append(
                    SkillRecord(
                        id=sid,
                        description=f"[{pack_id}] {desc}",
                        parameters=params,
                        handler=handler,
                        extends_skill_id=ext,
                    ),
                )
                seen_ids.add(sid)
    return out


def list_pack_manifests() -> list[dict[str, Any]]:
    """Catalog for operators / UI (read-only)."""
    rows: list[dict[str, Any]] = []
    for base in _pack_dirs():
        for manifest_path in sorted(base.glob("*/manifest.json")):
            try:
                data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            rows.append(
                {
                    "path": str(manifest_path),
                    "pack_id": data.get("pack_id"),
                    "version": data.get("version"),
                    "title": data.get("title"),
                    "skill_count": len(data.get("skills") or []),
                },
            )
    return rows
