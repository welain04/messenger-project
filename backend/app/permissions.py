"""RBAC: права (permissions) и их сопоставление с ролями.

MVP-вариант (Этап 2): маппинг роль -> набор прав хранится в коде. Проверки в
роутерах выполняются через require_permission(...) из app/deps.py, поэтому при
переходе на хранение прав в БД (Этап 6) места вызова не изменятся — поменяется
только источник данных в этом модуле.

Контекстные (chat-scoped) права (например, владелец чата управляет участниками
своего чата) проверяются дополнительно в самих роутерах поверх глобальных прав.
"""

from __future__ import annotations

from enum import Enum

from .models import UserRole


class Permission(str, Enum):
    CREATE_CHAT = "create_chat"
    CREATE_GROUP_CHAT = "create_group_chat"
    EDIT_OWN_MESSAGE = "edit_own_message"
    DELETE_OWN_MESSAGE = "delete_own_message"
    PIN_MESSAGE = "pin_message"
    EDIT_CHAT = "edit_chat"
    MANAGE_CHAT_MEMBERS = "manage_chat_members"
    DELETE_ANY_MESSAGE = "delete_any_message"
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    SUSPEND_USER = "suspend_user"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    MANAGE_SYSTEM_SETTINGS = "manage_system_settings"


# Базовый набор для обычного пользователя.
# Решение проекта: создавать группы могут все аутентифицированные пользователи.
_STUDENT: set[Permission] = {
    Permission.CREATE_CHAT,
    Permission.CREATE_GROUP_CHAT,
    Permission.EDIT_OWN_MESSAGE,
    Permission.DELETE_OWN_MESSAGE,
}

# Куратор = модерация чатов/сообщений.
_CURATOR: set[Permission] = _STUDENT | {
    Permission.PIN_MESSAGE,
    Permission.EDIT_CHAT,
    Permission.MANAGE_CHAT_MEMBERS,
    Permission.DELETE_ANY_MESSAGE,
}

# Админ = всё кураторское + управление пользователями/системой.
_ADMIN: set[Permission] = _CURATOR | {
    Permission.MANAGE_USERS,
    Permission.MANAGE_ROLES,
    Permission.SUSPEND_USER,
    Permission.VIEW_AUDIT_LOGS,
    Permission.MANAGE_SYSTEM_SETTINGS,
}

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.student: _STUDENT,
    UserRole.curator: _CURATOR,
    UserRole.admin: _ADMIN,
}


def role_permissions(role: UserRole) -> set[Permission]:
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: UserRole, perm: Permission) -> bool:
    return perm in role_permissions(role)
