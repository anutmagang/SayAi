from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base
from app.db.models import api_key as api_key_model  # noqa: F401
from app.db.models import chat_message as chat_message_model  # noqa: F401
from app.db.models import chat_session as chat_session_model  # noqa: F401
from app.db.models import rag_collection as rag_collection_model  # noqa: F401
from app.db.models import rag_document as rag_document_model  # noqa: F401
from app.db.models import run as run_model  # noqa: F401
from app.db.models import run_step as run_step_model  # noqa: F401
from app.db.models import skill_discovery_draft as skill_discovery_draft_model  # noqa: F401
from app.db.models import user as user_model  # noqa: F401
from app.db.models import user_skill_setting as user_skill_setting_model  # noqa: F401
from app.db.models import workflow as workflow_model  # noqa: F401
from app.db.models import workflow_run as workflow_run_model  # noqa: F401
from app.db.models import workflow_run_step as workflow_run_step_model  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required for migrations")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
