"""Password hashing and JWT helpers.

Passwords are hashed with bcrypt directly (not passlib) to avoid the known
passlib/bcrypt 4+ incompatibility warning and to keep the dependency surface
small.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

_BCRYPT_ROUNDS = 12
_MAX_PASSWORD_BYTES = 72  # bcrypt hard limit


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")
    if len(pw) > _MAX_PASSWORD_BYTES:
        # bcrypt truncates silently; reject instead so behaviour is explicit.
        raise ValueError("Password is too long (max 72 bytes).")
    return bcrypt.hashpw(pw, bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    *,
    subject: str,
    org_id: str,
    role: str,
    expires_delta: dt.timedelta | None = None,
) -> str:
    now = dt.datetime.now(dt.UTC)
    expire = now + (
        expires_delta
        or dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "org": org_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        return None
