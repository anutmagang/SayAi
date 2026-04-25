from __future__ import annotations

from typing import Any

from app.skills.builtin import BUILTIN
from app.skills.pack_loader import load_pack_skill_records
from app.skills.records import SkillRecord


def _fn_name(skill_id: str) -> str:
    return skill_id.replace(".", "_")


def _build_fn_index(skills: list[SkillRecord]) -> dict[str, str]:
    return {_fn_name(s.id): s.id for s in skills}


def load_skills() -> list[SkillRecord]:
    builtins = [
        SkillRecord(
            id=item["id"],
            description=item["description"],
            parameters=item["parameters"],
            handler=item["handler"],
            extends_skill_id=None,
        )
        for item in BUILTIN
    ]
    builtin_ids = {s.id for s in builtins}
    packs = [s for s in load_pack_skill_records() if s.id not in builtin_ids]
    return [*builtins, *packs]


def filter_skills(allowlist: list[str], skills: list[SkillRecord]) -> list[SkillRecord]:
    if not allowlist or "*" in allowlist:
        return skills
    allow = set(allowlist)
    return [s for s in skills if s.id in allow]


def tools_openai_schema(skills: list[SkillRecord]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    fn_index = _build_fn_index(skills)
    tools: list[dict[str, Any]] = []
    for s in skills:
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": _fn_name(s.id),
                    "description": s.description,
                    "parameters": s.parameters,
                },
            }
        )
    return tools, fn_index


def resolve_skill_id(function_name: str, fn_index: dict[str, str]) -> str | None:
    return fn_index.get(function_name)
