from __future__ import annotations

from sqlalchemy import text

from app.db.session import get_session_factory


def postgres_available() -> bool:
    try:
        factory = get_session_factory()
        db = factory()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        return True
    except Exception:
        return False
