from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.models.user import User
from app.skills.pack_loader import list_pack_manifests

router = APIRouter()


@router.get("/skill-packs")
def list_skill_packs(_user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Catalog of on-disk pack manifests (loaded at process start; no separate install API)."""
    return {"packs": list_pack_manifests()}
