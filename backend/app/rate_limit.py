"""Простой in-memory rate limiter для MVP.

Скользящее окно по ключу (по умолчанию — IP клиента). Потокобезопасен:
sync-эндпоинты FastAPI выполняются в пуле потоков, поэтому используем Lock.

Ограничения (осознанно для MVP):
- состояние хранится в памяти процесса -> при нескольких воркерах лимиты
  считаются раздельно. На этапе масштабирования заменяется на Redis без
  изменения мест вызова (интерфейс-зависимость остаётся прежним).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from .config import get_settings

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _hit(key: str, limit: int, window_seconds: float) -> bool:
    """Возвращает True, если запрос в пределах лимита; иначе False."""
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def _client_ip(request: Request) -> str:
    settings = get_settings()
    # X-Forwarded-For учитываем только при явном доверии к прокси, иначе его
    # легко подделать и обойти лимит. Заголовок строится слева направо
    # (leftmost — исходный клиент, rightmost — ближайший прокси); каждый
    # доверенный прокси добавляет один элемент справа, поэтому реальный клиент
    # находится на позиции -TRUSTED_PROXY_COUNT.
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
    """Сброс состояния (для тестов)."""
    with _lock:
        _buckets.clear()


class RateLimiter:
    """FastAPI-зависимость: ограничивает число запросов на ключ за окно.

    Использование:
        login_limit = RateLimiter(limit=5, window_seconds=60, scope="login")
        @router.post("/login", dependencies=[Depends(login_limit)])
    """

    def __init__(self, limit: int, window_seconds: float, scope: str) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.scope = scope

    def __call__(self, request: Request) -> None:
        # limit <= 0 -> лимитирование отключено.
        if self.limit <= 0:
            return
        key = f"{self.scope}:{_client_ip(request)}"
        if not _hit(key, self.limit, self.window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Слишком много запросов. Попробуйте позже",
            )
