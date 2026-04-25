from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.models.user_skill_setting import UserSkillSetting
from app.db.session import get_db
from app.skills.registry import load_skills

router = APIRouter()


class SkillSettingPatch(BaseModel):
    enabled: bool | None = None
    config: dict[str, Any] | None = None


class SkillSettingOut(BaseModel):
    id: str
    description: str
    parameters: dict[str, Any]
    enabled: bool
    config: dict[str, Any]


@router.get("/skills")
def list_skills(_user: User = Depends(get_current_user)) -> list[dict[str, Any]]:
    skills = load_skills()
    return [
        {
            "id": s.id,
            "description": s.description,
            "parameters": s.parameters,
        }
        for s in skills
    ]


@router.get("/skills/settings", response_model=list[SkillSettingOut])
def list_skill_settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SkillSettingOut]:
    rows = db.scalars(select(UserSkillSetting).where(UserSkillSetting.user_id == user.id)).all()
    by_skill = {r.skill_id: r for r in rows}

    out: list[SkillSettingOut] = []
    for s in load_skills():
        row = by_skill.get(s.id)
        out.append(
            SkillSettingOut(
                id=s.id,
                description=s.description,
                parameters=s.parameters,
                enabled=True if row is None else bool(row.enabled),
                config={} if row is None else dict(row.config or {}),
            )
        )
    return out


@router.patch("/skills/settings/{skill_id}", response_model=SkillSettingOut)
def patch_skill_setting(
    skill_id: str,
    body: SkillSettingPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillSettingOut:
    allowed = {s.id for s in load_skills()}
    if skill_id not in allowed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown skill")

    row = db.scalars(
        select(UserSkillSetting).where(
            UserSkillSetting.user_id == user.id,
            UserSkillSetting.skill_id == skill_id,
        )
    ).first()

    if row is None:
        row = UserSkillSetting(
            user_id=user.id,
            skill_id=skill_id,
            enabled=True if body.enabled is None else bool(body.enabled),
            config=body.config if body.config is not None else {},
        )
        db.add(row)
    else:
        if body.enabled is not None:
            row.enabled = bool(body.enabled)
        if body.config is not None:
            row.config = body.config
        db.add(row)

    db.commit()
    db.refresh(row)

    meta = next(s for s in load_skills() if s.id == skill_id)
    return SkillSettingOut(
        id=meta.id,
        description=meta.description,
        parameters=meta.parameters,
        enabled=bool(row.enabled),
        config=dict(row.config or {}),
    )


@router.delete(
    "/skills/settings/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_skill_setting(
    skill_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = db.scalars(
        select(UserSkillSetting).where(
            UserSkillSetting.user_id == user.id,
            UserSkillSetting.skill_id == skill_id,
        )
    ).first()
    if row is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
