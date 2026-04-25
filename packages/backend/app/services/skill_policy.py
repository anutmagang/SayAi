from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.user_skill_setting import UserSkillSetting
from app.skills.records import SkillRecord
from app.skills.registry import load_skills


def load_skills_for_user(db: Session, user_id: UUID) -> list[SkillRecord]:
    """Return built-in skills minus those explicitly disabled for this user."""
    rows = db.scalars(select(UserSkillSetting).where(UserSkillSetting.user_id == user_id)).all()
    disabled = {r.skill_id for r in rows if r.enabled is False}

    return [s for s in load_skills() if s.id not in disabled]
