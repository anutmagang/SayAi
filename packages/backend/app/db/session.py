from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine = None
SessionLocal: sessionmaker[Session] | None = None


def configure_engine() -> None:
    global _engine, SessionLocal
    if _engine is not None and SessionLocal is not None:
        return
    settings = get_settings()
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 5},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_session_factory() -> sessionmaker[Session]:
    configure_engine()
    assert SessionLocal is not None
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
