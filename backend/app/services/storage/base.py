"""Абстракция объектного хранилища (S3-compatible / local)."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

logger = logging.getLogger("messenger.storage")


class StorageError(Exception):
    """Ошибка провайдера хранилища."""

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    size_bytes: int
    content_type: str
    etag: str | None = None
    provider: str = ""


@dataclass(frozen=True)
class SignedUrl:
    url: str
    expires_at: datetime
    storage_key: str


class StorageService(ABC):
    """Провайдер-agnostic интерфейс. Роутеры работают только через FileService."""

    provider_name: str = "unknown"

    def _log_request(self, operation: str, **kwargs: object) -> None:
        safe = {k: v for k, v in kwargs.items() if k not in ("data", "secret", "body")}
        logger.info("storage request op=%s provider=%s %s", operation, self.provider_name, safe)

    def _log_response(self, operation: str, **kwargs: object) -> None:
        logger.info("storage response op=%s provider=%s %s", operation, self.provider_name, kwargs)

    def _log_error(self, operation: str, exc: Exception, **kwargs: object) -> None:
        logger.error(
            "storage error op=%s provider=%s error=%s %s",
            operation,
            self.provider_name,
            exc,
            kwargs,
            exc_info=True,
        )

    @abstractmethod
    def put_object(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        raise NotImplementedError

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_presigned_get_url(
        self,
        key: str,
        ttl_seconds: int,
        *,
        filename: str | None = None,
    ) -> SignedUrl:
        raise NotImplementedError

    def copy_object(self, source_key: str, dest_key: str) -> StoredObject:
        """Копирование объекта (опционально переопределяется провайдером)."""
        raise StorageError(f"copy_object не поддерживается провайдером {self.provider_name}")
