"""Инициализация Sentry для FastAPI."""

from __future__ import annotations

import logging

import sentry_sdk
from fastapi.exceptions import RequestValidationError
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from starlette.exceptions import HTTPException

from .config import Settings

logger = logging.getLogger("messenger")


def _before_send(event: dict, hint: dict) -> dict | None:
    """Не отправляем ожидаемые клиентские ошибки (422, 4xx)."""
    exc_info = hint.get("exc_info")
    if exc_info:
        _, exc_value, _ = exc_info
        if isinstance(exc_value, (RequestValidationError, HTTPException)):
            return None
    return event


def init_sentry(settings: Settings) -> None:
    dsn = settings.SENTRY_DSN.strip()
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.APP_ENV,
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
        before_send=_before_send,
    )
    logger.info("Sentry initialized environment=%s", settings.APP_ENV)
