"""Structured JSON log helpers (access, business, error events)."""

from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .log_sanitize import sanitize_dict

EVENT_ACCESS = "http_request"
EVENT_BUSINESS = "business"
EVENT_ERROR = "error"
EVENT_STORAGE = "storage"

_access_logger = logging.getLogger("messenger.access")
_business_logger = logging.getLogger("messenger.business")
_error_logger = logging.getLogger("messenger.error")
_storage_logger = logging.getLogger("messenger.storage")


def _format_summary(event: str, fields: dict[str, Any]) -> str:
    if event == EVENT_ACCESS:
        return (
            f"{fields.get('method')} {fields.get('path')} "
            f"{fields.get('status')} {fields.get('duration_ms')}ms"
        )
    if event == EVENT_BUSINESS:
        action = fields.get("action", "business")
        entity = fields.get("entity_type", "")
        return f"{action} ({entity})"
    if event == EVENT_ERROR:
        return f"{fields.get('exc_type')}: {fields.get('error_message')}"
    if event == EVENT_STORAGE:
        return (
            f"storage {fields.get('phase')} op={fields.get('operation')} "
            f"provider={fields.get('provider')}"
        )
    return event


def _uuid_str(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _emit(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    clean = sanitize_dict(fields)
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": logging.getLevelName(level),
        "logger": logger.name,
        "event": event,
        "message": _format_summary(event, clean),
        **clean,
    }
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def log_http_request(
    *,
    method: str,
    path: str,
    status: int,
    duration_ms: float,
    user_id: UUID | None = None,
    client_ip: str | None = None,
    request_id: str | None = None,
) -> None:
    _emit(
        _access_logger,
        logging.INFO,
        EVENT_ACCESS,
        method=method,
        path=path,
        status=status,
        duration_ms=round(duration_ms, 2),
        user_id=_uuid_str(user_id),
        client_ip=client_ip,
        request_id=request_id,
    )


def log_business_event(
    *,
    action: str,
    entity_type: str,
    actor_id: UUID | None = None,
    entity_id: UUID | str | None = None,
    data: dict | None = None,
) -> None:
    _emit(
        _business_logger,
        logging.INFO,
        EVENT_BUSINESS,
        action=action,
        entity_type=entity_type,
        actor_id=_uuid_str(actor_id),
        entity_id=_uuid_str(entity_id) if isinstance(entity_id, UUID) else entity_id,
        data=data,
    )


def log_error_event(
    *,
    exc: BaseException,
    method: str | None = None,
    path: str | None = None,
    user_id: UUID | None = None,
    request_id: str | None = None,
    status: int = 500,
) -> None:
    _emit(
        _error_logger,
        logging.ERROR,
        EVENT_ERROR,
        error_message=str(exc),
        exc_type=type(exc).__name__,
        stack="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        method=method,
        path=path,
        status=status,
        user_id=_uuid_str(user_id),
        request_id=request_id,
    )


def log_storage_event(
    *,
    phase: str,
    operation: str,
    provider: str,
    **fields: Any,
) -> None:
    level = logging.ERROR if phase == "error" else logging.INFO
    _emit(
        _storage_logger,
        level,
        EVENT_STORAGE,
        phase=phase,
        operation=operation,
        provider=provider,
        **fields,
    )
