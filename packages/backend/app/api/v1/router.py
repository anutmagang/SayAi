from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    auth,
    health,
    observability,
    project_inspector,
    rag,
    runs,
    skill_drafts,
    skill_packs,
    skills_meta,
    workflows_api,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(runs.router, tags=["runs"])
api_router.include_router(skills_meta.router, tags=["skills"])
api_router.include_router(skill_drafts.router, tags=["skill-drafts"])
api_router.include_router(skill_packs.router, tags=["skill-packs"])
api_router.include_router(project_inspector.router, tags=["project"])
api_router.include_router(rag.router, tags=["rag"])
api_router.include_router(workflows_api.router, tags=["workflows"])
api_router.include_router(observability.router, tags=["observability"])
