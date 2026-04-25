from __future__ import annotations

import logging

import httpx
import redis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import get_session_factory

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(response: Response) -> dict[str, str | bool]:
    settings = get_settings()
    checks: dict[str, bool] = {"database": False, "redis": False, "qdrant": True}

    try:
        factory = get_session_factory()
        db = factory()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = True
        finally:
            db.close()
    except Exception:
        logger.exception("Database readiness check failed")

    try:
        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        checks["redis"] = bool(r.ping())
    except Exception:
        logger.exception("Redis readiness check failed")

    if settings.qdrant_url:
        checks["qdrant"] = False
        try:
            url = settings.qdrant_url.rstrip("/") + "/readyz"
            resp = httpx.get(url, timeout=2.0)
            checks["qdrant"] = resp.status_code == 200
        except Exception:
            logger.exception("Qdrant readiness check failed")

    ok = all(checks.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ok else "degraded", **checks}
