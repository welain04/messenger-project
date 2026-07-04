"""Бэкенды rate limit: in-memory (MVP) и заготовка Redis для масштабирования."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from threading import Lock

logger = logging.getLogger("messenger.rate_limit")


class RateLimitBackend(ABC):
    @abstractmethod
    def hit(self, key: str, limit: int, window_seconds: float) -> bool:
        """Возвращает True, если запрос в пределах лимита; иначе False."""


class MemoryRateLimitBackend(RateLimitBackend):
    """Скользящее окно в памяти процесса (потокобезопасно)."""

    def __init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str, limit: int, window_seconds: float) -> bool:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


class RedisRateLimitBackend(RateLimitBackend):
    """Заготовка под общий счётчик при нескольких воркерах/инстансах.

    Реализация будет добавлена при подключении Redis (redis-py).
    """

    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url

    def hit(self, key: str, limit: int, window_seconds: float) -> bool:
        raise NotImplementedError(
            "Redis rate limit backend пока не реализован. "
            "Используйте RATE_LIMIT_BACKEND=memory или дождитесь поддержки Redis."
        )


def create_rate_limit_backend(backend: str, redis_url: str) -> RateLimitBackend:
    name = backend.strip().lower()
    if name == "redis":
        if not redis_url.strip():
            raise ValueError("RATE_LIMIT_BACKEND=redis требует непустой REDIS_URL")
        logger.info("Rate limit backend: redis (stub)")
        return RedisRateLimitBackend(redis_url.strip())
    if name not in ("memory", ""):
        raise ValueError(
            f"Неизвестный RATE_LIMIT_BACKEND={backend!r}. Допустимо: memory, redis."
        )
    return MemoryRateLimitBackend()
