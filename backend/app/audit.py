"""Запись событий аудита.

Тонкая обёртка над storage.create_audit_log с единым набором имён действий
(namespaced: "auth.login", "user.role_changed" и т.п.). Запись аудита не должна
ронять основное действие, поэтому ошибки логируются, но не пробрасываются.

Ограничение MVP: запись аудита выполняется отдельным INSERT после основного
действия (а не в одной транзакции). Для критичных событий этого достаточно;
переход к транзакционной записи возможен на этапе перехода к PostgreSQL.
"""

from __future__ import annotations

import logging
from uuid import UUID

from . import storage
from .structured_log import log_business_event

logger = logging.getLogger("app.audit")


# Критичные для безопасности события (для будущих алертов/выборок).
CRITICAL_ACTIONS = {
    "auth.login_failed",
    "auth.refresh_reuse_detected",
    "auth.password_changed",
    "auth.password_reset",
    "user.role_changed",
    "user.suspended",
    "user.activated",
}


def record(
    action: str,
    entity_type: str,
    actor_id: UUID | None = None,
    entity_id: str | UUID | None = None,
    data: dict | None = None,
) -> None:
    try:
        storage.create_audit_log(
            action=action,
            entity_type=entity_type,
            actor_id=actor_id,
            entity_id=entity_id,
            data=data,
        )
        log_business_event(
            action=action,
            entity_type=entity_type,
            actor_id=actor_id,
            entity_id=entity_id,
            data=data,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Не удалось записать событие аудита: %s", action)
