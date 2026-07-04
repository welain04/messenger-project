"""Зависимости FastAPI для аутентификации и авторизации (RBAC)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import storage
from .models import UserInDB, UserRole
from .permissions import Permission, has_permission
from .security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def _user_from_payload(payload: dict | None) -> UserInDB | None:
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


def _sid_from_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    sid = getattr(request.state, "sid", None)
    if sid:
        return str(sid)
    if credentials is not None:
        payload = decode_access_token(credentials.credentials)
        if payload and payload.get("sid"):
            return str(payload["sid"])
    return None


def _ensure_active_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    """Access-токен привязан к сессии (sid): отозванная сессия -> 401."""
    sid = _sid_from_request(request, credentials)
    if sid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия недействительна. Войдите снова",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        session_id = UUID(sid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия недействительна. Войдите снова",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    if not storage.is_session_active(session_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия недействительна. Войдите снова",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _user_from_token(token: str | None) -> UserInDB | None:
    if not token:
        return None
    return _user_from_payload(decode_access_token(token))


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserInDB:
    """Достаём пользователя из request.state / Bearer и проверяем активность сессии."""
    user: UserInDB | None = getattr(request.state, "user", None)
    if user is None and credentials is not None:
        user = _user_from_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован. Войдите в систему",
            headers={"WWW-Authenticate": "Bearer"},
        )
    _ensure_active_session(request, credentials)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован. Обратитесь к администратору",
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
    if user is None:
        return None
    try:
        _ensure_active_session(request, credentials)
    except HTTPException:
        return None
    if not user.is_active:
        return None
    return user


def require_permission(perm: Permission) -> Callable[[UserInDB], UserInDB]:
    """Зависимость: требует у текущего пользователя конкретное право (RBAC)."""

    def _dependency(current: UserInDB = Depends(get_current_user)) -> UserInDB:
        if not has_permission(current.role, perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для этого действия",
            )
        return current

    return _dependency


def require_verified_email(
    current: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Зависимость: действие доступно только с подтверждённым email."""
    if not current.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Подтвердите email, чтобы пользоваться мессенджером",
        )
    return current


def require_role(*roles: UserRole) -> Callable[[UserInDB], UserInDB]:
    """Зависимость: требует, чтобы роль пользователя была одной из указанных."""

    def _dependency(current: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для этого действия",
            )
        return current

    return _dependency
