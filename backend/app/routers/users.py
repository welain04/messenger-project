from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from .. import audit, storage
from ..config import get_settings
from ..deps import get_current_user, require_verified_email
from ..deps_storage import get_file_service
from ..models import UserInDB, UserRole
from ..rate_limit import RateLimiter
from ..schemas import (
    ChangePasswordRequest,
    MePrivate,
    RoleUpgradeCreate,
    RoleUpgradeOut,
    SessionOut,
    UserPublic,
    UserUpdateRequest,
)
from ..security import hash_password, verify_password
from ..services.files import FileService

router = APIRouter(prefix="/users", tags=["users"])

_settings = get_settings()
_search_rate_limit = RateLimiter(_settings.RATE_LIMIT_SEARCH_PER_MIN, 60, "user_search")


@router.get("/me", response_model=MePrivate)
def read_me(current: UserInDB = Depends(get_current_user)) -> MePrivate:
    return MePrivate.model_validate(current)


@router.post("/me/avatar", response_model=MePrivate)
async def upload_avatar(
    file: UploadFile = File(...),
    current: UserInDB = Depends(require_verified_email),
    files: FileService = Depends(get_file_service),
) -> MePrivate:
    updated = files.upload_avatar(current, file)
    return MePrivate.model_validate(updated)


@router.delete("/me/avatar", response_model=MePrivate)
def delete_avatar(
    current: UserInDB = Depends(get_current_user),
    files: FileService = Depends(get_file_service),
) -> MePrivate:
    updated = files.delete_avatar(current)
    return MePrivate.model_validate(updated)


@router.patch("/me", response_model=MePrivate)
def update_me(
    payload: UserUpdateRequest,
    current: UserInDB = Depends(get_current_user),
) -> MePrivate:
    new_nick = payload.nickname
    existing = storage.get_user_by_nickname(new_nick)
    if existing and existing.id != current.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот никнейм уже занят")
    old_nick = current.nickname
    storage.update_nickname(current.id, new_nick)
    current.nickname = new_nick
    if old_nick != new_nick:
        audit.record(
            "user.nickname_changed",
            "user",
            actor_id=current.id,
            entity_id=current.id,
            data={"old": old_nick, "new": new_nick},
        )
    return MePrivate.model_validate(current)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    current: UserInDB = Depends(get_current_user),
) -> None:
    if not verify_password(payload.current_password, current.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Текущий пароль указан неверно")
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Новый пароль должен отличаться от текущего",
        )

    storage.update_password(current.id, hash_password(payload.new_password))
    storage.revoke_all_sessions(current.id)
    audit.record(
        "auth.password_changed",
        "user",
        actor_id=current.id,
        entity_id=current.id,
    )


@router.post(
    "/me/role-upgrade-request",
    response_model=RoleUpgradeOut,
    status_code=status.HTTP_201_CREATED,
)
def request_role_upgrade(
    payload: RoleUpgradeCreate,
    current: UserInDB = Depends(require_verified_email),
) -> RoleUpgradeOut:
    if current.role != UserRole.student:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Запросить повышение может только ученик",
        )
    if storage.get_pending_request_for_user(current.id) is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "У вас уже есть заявка на рассмотрении",
        )

    row = storage.create_role_upgrade_request(current.id, "curator", payload.reason)
    audit.record(
        "role_request.created",
        "role_upgrade_request",
        actor_id=current.id,
        entity_id=row["id"],
        data={"requested_role": "curator"},
    )
    return RoleUpgradeOut.model_validate(dict(row))


@router.get("/me/role-upgrade-requests", response_model=list[RoleUpgradeOut])
def my_role_upgrade_requests(
    current: UserInDB = Depends(get_current_user),
) -> list[RoleUpgradeOut]:
    rows = storage.list_role_upgrade_requests_for_user(current.id)
    return [RoleUpgradeOut.model_validate(dict(r)) for r in rows]


@router.get("/me/sessions", response_model=list[SessionOut])
def my_sessions(
    request: Request,
    current: UserInDB = Depends(get_current_user),
) -> list[SessionOut]:
    current_sid = getattr(request.state, "sid", None)
    sessions: list[SessionOut] = []
    for row in storage.list_active_sessions(current.id):
        sessions.append(
            SessionOut(
                id=UUID(row["id"]),
                user_agent=row["user_agent"],
                ip=row["ip"],
                created_at=row["created_at"],
                last_seen_at=row["last_seen_at"],
                current=str(row["id"]) == str(current_sid),
            )
        )
    return sessions


@router.delete("/me/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_my_session(
    session_id: UUID,
    current: UserInDB = Depends(get_current_user),
) -> None:
    row = storage.get_session(session_id)
    if row is None or str(row["user_id"]) != str(current.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сессия не найдена")
    storage.revoke_session(session_id)


@router.get(
    "/search",
    response_model=list[UserPublic],
    dependencies=[Depends(_search_rate_limit)],
)
def search_users(
    q: str = Query(..., min_length=1, max_length=30),
    limit: int = Query(10, ge=1, le=20),
    current: UserInDB = Depends(require_verified_email),
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
    _: UserInDB = Depends(require_verified_email),
) -> UserPublic:
    """Публичная карточка пользователя — нужна, чтобы показывать никнеймы
    собеседников в шапке чата и в Sidebar."""
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return UserPublic.model_validate(user)
