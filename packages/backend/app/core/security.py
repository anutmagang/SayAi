from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt


def _password_bytes(plain: str) -> bytes:
    """bcrypt accepts at most 72 bytes."""
    b = plain.encode("utf-8")
    return b[:72] if len(b) > 72 else b


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_password_bytes(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(plain), hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(*, subject: str, secret: str, algorithm: str, expires_minutes: int) -> str:
    now = datetime.now(tz=UTC)
    expire = now + timedelta(minutes=expires_minutes)
    payload: dict[str, Any] = {"sub": subject, "iat": now, "exp": expire, "typ": "access"}
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=[algorithm])


def verify_token_subject(token: str, *, secret: str, algorithm: str) -> str | None:
    try:
        payload = decode_token(token=token, secret=secret, algorithm=algorithm)
        sub = payload.get("sub")
        if isinstance(sub, str) and sub:
            return sub
    except JWTError:
        return None
    return None


def generate_api_key() -> tuple[str, str, str]:
    """Return (full_key, prefix, key_hash_hex)."""
    raw = secrets.token_urlsafe(32)
    full = f"sayai_{raw}"
    prefix = full[:16]
    digest = hashlib.sha256(full.encode("utf-8")).hexdigest()
    return full, prefix, digest


def hash_api_key(full_key: str) -> str:
    return hashlib.sha256(full_key.encode("utf-8")).hexdigest()
