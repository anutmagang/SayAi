from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.skill_discovery_draft import SkillDiscoveryDraft
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter()

StatusLiteral = Literal["draft", "submitted", "archived"]
class SkillDraftCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    body: dict[str, Any] = Field(default_factory=dict)
    status: StatusLiteral = "draft"


class SkillDraftPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=240)
    body: dict[str, Any] | None = None
    status: StatusLiteral | None = None


class SkillDraftOut(BaseModel):
    id: UUID
    title: str
    status: str
    body: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


@router.get("/skill-drafts", response_model=list[SkillDraftOut])
def list_drafts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SkillDiscoveryDraft]:
    rows = db.scalars(
        select(SkillDiscoveryDraft)
        .where(SkillDiscoveryDraft.user_id == user.id)
        .order_by(SkillDiscoveryDraft.updated_at.desc())
    ).all()
    return list(rows)


@router.post("/skill-drafts", response_model=SkillDraftOut)
def create_draft(
    body: SkillDraftCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillDiscoveryDraft:
    row = SkillDiscoveryDraft(
        user_id=user.id,
        title=body.title,
        status=body.status,
        body=dict(body.body or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/skill-drafts/{draft_id}", response_model=SkillDraftOut)
def get_draft(
    draft_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillDiscoveryDraft:
    row = db.get(SkillDiscoveryDraft, draft_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row


@router.patch("/skill-drafts/{draft_id}", response_model=SkillDraftOut)
def patch_draft(
    draft_id: UUID,
    body: SkillDraftPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillDiscoveryDraft:
    row = db.get(SkillDiscoveryDraft, draft_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if body.title is not None:
        row.title = body.title
    if body.body is not None:
        row.body = body.body
    if body.status is not None:
        row.status = body.status
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "/skill-drafts/{draft_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_draft(
    draft_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = db.get(SkillDiscoveryDraft, draft_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
