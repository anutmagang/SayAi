from __future__ import annotations

import os

os.environ.setdefault("SECRET_KEY", "ci-test-secret-key-must-be-long-enough-32")
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+psycopg://sayai:sayai@127.0.0.1:5432/sayai"),
)
os.environ.setdefault("REDIS_URL", os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0"))
os.environ.setdefault("QDRANT_URL", "")
