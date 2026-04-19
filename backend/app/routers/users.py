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
    existing = storage.user_by_nickname.get(new_nick.lower())
    if existing and existing != current.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Nickname already taken")
    storage.rename_user(current, new_nick)
    return UserPublic.model_validate(current)


@router.get("/search", response_model=list[UserPublic])
def search_users(
    q: str = Query(..., min_length=1, max_length=30),
    limit: int = Query(10, ge=1, le=20),
    current: UserInDB = Depends(get_current_user),
) -> list[UserPublic]:
    """Поиск пользователей по nickname (case-insensitive)."""
    q_norm = q.strip().lower()
    if not q_norm:
        return []

    found = [
        u
        for u in storage.users.values()
        if u.id != current.id and q_norm in u.nickname.lower()
    ]
    found.sort(key=lambda u: u.nickname.lower())
    return [UserPublic.model_validate(u) for u in found[:limit]]


@router.get("/{user_id}", response_model=UserPublic)
def read_user(
    user_id: UUID,
    _: UserInDB = Depends(get_current_user),
) -> UserPublic:
    """Публичная карточка пользователя — нужна, чтобы показывать никнеймы
    собеседников в шапке чата и в Sidebar."""
    user = storage.users.get(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserPublic.model_validate(user)
