from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import storage
from ..deps import get_current_user
from ..models import UserInDB
from ..schemas import UserPublic, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def read_me(current: UserInDB = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(current)


@router.patch("/me", response_model=UserPublic)
def update_me(
    payload: UserUpdateRequest,
    current: UserInDB = Depends(get_current_user),
) -> UserPublic:
    new_nick = payload.nickname
    existing = storage.get_user_by_nickname(new_nick)
    if existing and existing.id != current.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот никнейм уже занят")
    storage.update_nickname(current.id, new_nick)
    current.nickname = new_nick
    return UserPublic.model_validate(current)


@router.get("/search", response_model=list[UserPublic])
def search_users(
    q: str = Query(..., min_length=1, max_length=30),
    limit: int = Query(10, ge=1, le=20),
    current: UserInDB = Depends(get_current_user),
) -> list[UserPublic]:
    """Поиск пользователей по nickname (case-insensitive)."""
    q_norm = q.strip()
    if not q_norm:
        return []

    found = storage.search_users(q_norm, exclude_id=current.id, limit=limit)
    return [UserPublic.model_validate(u) for u in found]


@router.get("/{user_id}", response_model=UserPublic)
def read_user(
    user_id: UUID,
    _: UserInDB = Depends(get_current_user),
) -> UserPublic:
    """Публичная карточка пользователя — нужна, чтобы показывать никнеймы
    собеседников в шапке чата и в Sidebar."""
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return UserPublic.model_validate(user)
