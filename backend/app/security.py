"""Хеширование паролей, работа с JWT и одноразовыми токенами."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import get_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_token(num_bytes: int = 32) -> str:
    """Криптостойкий URL-safe токен (для подтверждения email и т.п.)."""
    return secrets.token_urlsafe(num_bytes)


def hash_token(token: str) -> str:
    """Детерминированный хэш токена для хранения в БД (сам токен не храним)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: UUID, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
