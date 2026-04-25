from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_api_key, verify_token_subject
from app.db.models.api_key import ApiKey
from app.db.models.user import User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def authenticate_user_token(db: Session, *, token: str | None) -> User | None:
    if not token:
        return None
    cfg = get_settings()

    if token.startswith("sayai_"):
        user = _user_from_api_key(db, token)
        if user is None or not user.is_active:
            return None
        return user

    sub = verify_token_subject(token, secret=cfg.secret_key, algorithm=cfg.jwt_algorithm)
    if sub is None:
        return None
    try:
        user_id = UUID(sub)
    except ValueError:
        return None

    user = db.scalars(select(User).where(User.id == user_id)).first()
    if user is None or not user.is_active:
        return None
    return user


def _user_from_api_key(db: Session, full_key: str) -> User | None:
    digest = hash_api_key(full_key)
    key = db.scalars(
        select(ApiKey).where(ApiKey.key_hash == digest, ApiKey.revoked_at.is_(None))
    ).first()
    if key is None:
        return None
    return db.scalars(select(User).where(User.id == key.user_id)).first()


def get_current_user(
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> User:
    token: str | None = None
    if creds is not None and creds.credentials:
        token = creds.credentials
    elif x_api_key:
        token = x_api_key

    user = authenticate_user_token(db, token=token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
