"""Глобальные обработчики необработанных исключений."""

from __future__ import annotations

import sentry_sdk
from fastapi import Request
from fastapi.responses import JSONResponse

from .config import get_settings
from .structured_log import log_error_event


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    user = getattr(request.state, "user", None)
    request_id = getattr(request.state, "request_id", None)
    log_error_event(
        exc=exc,
        method=request.method,
        path=request.url.path,
        user_id=user.id if user else None,
        request_id=request_id,
    )
    settings = get_settings()
    if settings.SENTRY_DSN.strip():
        sentry_sdk.capture_exception(exc)
    detail = "Внутренняя ошибка сервера" if settings.is_production else str(exc)
    return JSONResponse(status_code=500, content={"detail": detail})
