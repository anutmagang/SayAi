"""phase4 skill settings + observability indexes

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_skill_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_id", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_skill_settings_user_skill"),
    )
    op.create_index("ix_user_skill_settings_user_id", "user_skill_settings", ["user_id"])

    op.create_index("ix_runs_user_created", "runs", ["user_id", "created_at"])
    op.create_index("ix_workflow_runs_user_created", "workflow_runs", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_user_created", table_name="workflow_runs")
    op.drop_index("ix_runs_user_created", table_name="runs")
    op.drop_index("ix_user_skill_settings_user_id", table_name="user_skill_settings")
    op.drop_table("user_skill_settings")
