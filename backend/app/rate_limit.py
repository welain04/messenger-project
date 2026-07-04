"""Rate limiter: FastAPI-зависимость поверх настраиваемого бэкенда (memory / redis)."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from .config import get_settings
from .rate_limit_backends import MemoryRateLimitBackend, RateLimitBackend, create_rate_limit_backend

_backend: RateLimitBackend | None = None


def _get_backend() -> RateLimitBackend:
    global _backend
    if _backend is None:
        settings = get_settings()
        _backend = create_rate_limit_backend(settings.RATE_LIMIT_BACKEND, settings.REDIS_URL)
    return _backend


def _client_ip(request: Request) -> str:
    settings = get_settings()
    if settings.TRUST_PROXY_HEADERS:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                count = max(1, settings.TRUSTED_PROXY_COUNT)
                return parts[-count] if count <= len(parts) else parts[0]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def reset() -> None:
    """Сброс состояния in-memory бэкенда (для тестов)."""
    backend = _get_backend()
    if isinstance(backend, MemoryRateLimitBackend):
        backend.reset()


class RateLimiter:
    """FastAPI-зависимость: ограничивает число запросов на ключ за окно."""

    def __init__(self, limit: int, window_seconds: float, scope: str) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.scope = scope

    def __call__(self, request: Request) -> None:
        if self.limit <= 0:
            return
        key = f"{self.scope}:{_client_ip(request)}"
        if not _get_backend().hit(key, self.limit, self.window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Попробуйте позже",
            )
