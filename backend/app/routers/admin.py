"""Админские эндпоинты управления пользователями, ролями, заявками и аудитом."""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import audit, storage
from ..deps import require_permission
from ..models import UserInDB, UserRole
from ..permissions import Permission
from ..schemas import (
    AdminUserOut,
    AuditLogOut,
    RoleUpdateRequest,
    RoleUpgradeOut,
    RoleUpgradeReview,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _get_user_or_404(user_id: UUID) -> UserInDB:
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return user


def _audit_out(row) -> AuditLogOut:
    try:
        data = json.loads(row["data"]) if row["data"] else {}
    except (ValueError, TypeError):
        data = {}
    return AuditLogOut(
        id=UUID(row["id"]),
        actor_id=UUID(row["actor_id"]) if row["actor_id"] else None,
        action=row["action"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        data=data,
        created_at=row["created_at"],
    )


@router.get(
    "/users",
    response_model=list[AdminUserOut],
    dependencies=[Depends(require_permission(Permission.MANAGE_USERS))],
)
def list_users(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[AdminUserOut]:
    return [AdminUserOut.model_validate(u) for u in storage.list_users(limit, offset)]


@router.patch("/users/{user_id}/role", response_model=AdminUserOut)
def change_role(
    user_id: UUID,
    payload: RoleUpdateRequest,
    current: UserInDB = Depends(require_permission(Permission.MANAGE_ROLES)),
) -> AdminUserOut:
    target = _get_user_or_404(user_id)

    if target.id == current.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Нельзя менять собственную роль",
        )

    # Защита от потери последнего активного администратора.
    demoting_admin = target.role == UserRole.admin and payload.role != UserRole.admin
    if demoting_admin and storage.count_active_admins() <= 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Нельзя понизить последнего администратора",
        )

    old_role = target.role
    storage.set_role(target.id, payload.role)
    target.role = payload.role
    audit.record(
        "user.role_changed",
        "user",
        actor_id=current.id,
        entity_id=target.id,
        data={"old": old_role.value, "new": payload.role.value},
    )
    return AdminUserOut.model_validate(target)


@router.post("/users/{user_id}/suspend", response_model=AdminUserOut)
def suspend_user(
    user_id: UUID,
    current: UserInDB = Depends(require_permission(Permission.SUSPEND_USER)),
) -> AdminUserOut:
    target = _get_user_or_404(user_id)

    if target.id == current.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя заблокировать самого себя")

    if target.role == UserRole.admin and storage.count_active_admins() <= 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Нельзя заблокировать последнего администратора",
        )

    storage.set_active(target.id, False)
    storage.revoke_all_sessions(target.id)  # немедленно завершаем все сессии
    target.is_active = False
    audit.record(
        "user.suspended", "user", actor_id=current.id, entity_id=target.id
    )
    return AdminUserOut.model_validate(target)


@router.post("/users/{user_id}/activate", response_model=AdminUserOut)
def activate_user(
    user_id: UUID,
    current: UserInDB = Depends(require_permission(Permission.SUSPEND_USER)),
) -> AdminUserOut:
    target = _get_user_or_404(user_id)
    storage.set_active(target.id, True)
    target.is_active = True
    audit.record(
        "user.activated", "user", actor_id=current.id, entity_id=target.id
    )
    return AdminUserOut.model_validate(target)


# --------------------------- role upgrade requests ---------------------------


@router.get("/role-upgrade-requests", response_model=list[RoleUpgradeOut])
def list_role_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: UserInDB = Depends(require_permission(Permission.MANAGE_ROLES)),
) -> list[RoleUpgradeOut]:
    rows = storage.list_role_upgrade_requests(status_filter, limit, offset)
    return [RoleUpgradeOut.model_validate(dict(r)) for r in rows]


def _get_pending_request_or_error(request_id: UUID):
    row = storage.get_role_upgrade_request(request_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заявка не найдена")
    if row["status"] != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Заявка уже рассмотрена")
    return row


@router.post("/role-upgrade-requests/{request_id}/approve", response_model=RoleUpgradeOut)
def approve_role_request(
    request_id: UUID,
    payload: RoleUpgradeReview,
    current: UserInDB = Depends(require_permission(Permission.MANAGE_ROLES)),
) -> RoleUpgradeOut:
    row = _get_pending_request_or_error(request_id)
    target_id = UUID(row["user_id"])

    storage.set_role(target_id, UserRole.curator)
    storage.review_role_upgrade_request(request_id, "approved", current.id, payload.note)
    audit.record(
        "role_request.approved",
        "role_upgrade_request",
        actor_id=current.id,
        entity_id=request_id,
        data={"user_id": str(target_id), "granted_role": "curator"},
    )
    audit.record(
        "user.role_changed",
        "user",
        actor_id=current.id,
        entity_id=target_id,
        data={"new": "curator", "via": "role_request"},
    )
    return RoleUpgradeOut.model_validate(dict(storage.get_role_upgrade_request(request_id)))


@router.post("/role-upgrade-requests/{request_id}/reject", response_model=RoleUpgradeOut)
def reject_role_request(
    request_id: UUID,
    payload: RoleUpgradeReview,
    current: UserInDB = Depends(require_permission(Permission.MANAGE_ROLES)),
) -> RoleUpgradeOut:
    row = _get_pending_request_or_error(request_id)
    storage.review_role_upgrade_request(request_id, "rejected", current.id, payload.note)
    audit.record(
        "role_request.rejected",
        "role_upgrade_request",
        actor_id=current.id,
        entity_id=request_id,
        data={"user_id": row["user_id"]},
    )
    return RoleUpgradeOut.model_validate(dict(storage.get_role_upgrade_request(request_id)))


# --------------------------- audit logs ---------------------------


@router.get("/audit-logs", response_model=list[AuditLogOut])
def get_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    actor_id: UUID | None = Query(default=None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: UserInDB = Depends(require_permission(Permission.VIEW_AUDIT_LOGS)),
) -> list[AuditLogOut]:
    rows = storage.list_audit_logs(limit, offset, action, entity_type, actor_id)
    return [_audit_out(r) for r in rows]
