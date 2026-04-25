from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, generate_api_key, hash_password, verify_password
from app.db.models.api_key import ApiKey
from app.db.models.user import User, UserRole
from app.db.session import get_db

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    scopes: list[str] = Field(default_factory=lambda: ["*"])


class ApiKeySummary(BaseModel):
    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeySummary):
    secret: str


@router.post("/register", response_model=UserResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> User:
    existing = db.scalars(select(User).where(User.email == body.email)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    count = db.scalar(select(func.count()).select_from(User))
    role = UserRole.owner.value if count == 0 else UserRole.viewer.value

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalars(select(User).where(User.email == body.email)).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")

    settings = get_settings()
    token = create_access_token(
        subject=str(user.id),
        secret=settings.secret_key,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/api-keys", response_model=ApiKeyCreatedResponse)
def create_api_key(
    body: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyCreatedResponse:
    full, prefix, digest = generate_api_key()
    row = ApiKey(
        user_id=user.id,
        name=body.name,
        prefix=prefix,
        key_hash=digest,
        scopes=body.scopes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ApiKeyCreatedResponse(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        scopes=list(row.scopes or []),
        created_at=row.created_at,
        secret=full,
    )


@router.get("/api-keys", response_model=list[ApiKeySummary])
def list_api_keys(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApiKey]:
    rows = db.scalars(
        select(ApiKey)
        .where(ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None))
        .order_by(ApiKey.created_at.desc())
    ).all()
    return list(rows)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def revoke_api_key(
    key_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    row = db.scalars(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.user_id == user.id,
            ApiKey.revoked_at.is_(None),
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

    row.revoked_at = datetime.now(tz=UTC)
    db.add(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
