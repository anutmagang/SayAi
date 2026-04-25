from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.api_key import ApiKey
    from app.db.models.chat_session import ChatSession
    from app.db.models.rag_collection import RagCollection
    from app.db.models.run import Run
    from app.db.models.skill_discovery_draft import SkillDiscoveryDraft
    from app.db.models.user_skill_setting import UserSkillSetting
    from app.db.models.workflow import Workflow
    from app.db.models.workflow_run import WorkflowRun


class UserRole(StrEnum):
    owner = "owner"
    developer = "developer"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.viewer.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    api_keys: Mapped[list[ApiKey]] = relationship(
        "ApiKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_sessions: Mapped[list[ChatSession]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list[Run]] = relationship(
        "Run",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    rag_collections: Mapped[list[RagCollection]] = relationship(
        "RagCollection",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    workflows: Mapped[list[Workflow]] = relationship(
        "Workflow",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    workflow_runs: Mapped[list[WorkflowRun]] = relationship(
        "WorkflowRun",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    skill_settings: Mapped[list[UserSkillSetting]] = relationship(
        "UserSkillSetting",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    skill_discovery_drafts: Mapped[list[SkillDiscoveryDraft]] = relationship(
        "SkillDiscoveryDraft",
        back_populates="user",
        cascade="all, delete-orphan",
    )
