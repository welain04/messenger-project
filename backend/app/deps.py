"""Зависимости FastAPI для аутентификации."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import storage
from .models import UserInDB
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _user_from_token(token: str | None) -> UserInDB | None:
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    try:
        user_id = UUID(sub)
    except ValueError:
        return None
    return storage.get_user(user_id)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInDB:
    """Достаём пользователя либо из request.state (положил middleware),
    либо из Bearer-заголовка напрямую."""
    user: UserInDB | None = getattr(request.state, "user", None)
    if user is None and credentials is not None:
        user = _user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован. Войдите в систему",
            headers={"WWW-Authenticate": "Bearer"},
        )
    storage.touch_last_seen(user.id)
    return user


def get_current_user_or_none(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInDB | None:
    user: UserInDB | None = getattr(request.state, "user", None)
    if user is None and credentials is not None:
        user = _user_from_token(credentials.credentials)
    return user
