"""Фабрика StorageService по STORAGE_PROVIDER из конфигурации."""

from __future__ import annotations

import logging
from pathlib import Path

from ...config import Settings
from .base import StorageService
from .local import LocalFilesystemStorage
from .yandex_s3 import YandexObjectStorage

logger = logging.getLogger("messenger.storage")


def create_storage_service(settings: Settings) -> StorageService:
    provider = settings.STORAGE_PROVIDER.strip().lower()
    logger.info("storage factory init provider=%s", provider)

    if provider == "yandex":
        if not settings.S3_BUCKET or not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
            raise ValueError(
                "STORAGE_PROVIDER=yandex требует S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY в .env"
            )
        return YandexObjectStorage(
            endpoint_url=settings.S3_ENDPOINT,
            bucket=settings.S3_BUCKET,
            access_key=settings.S3_ACCESS_KEY,
            secret_key=settings.S3_SECRET_KEY,
            region=settings.S3_REGION,
        )

    if provider == "local":
        base = Path(settings.LOCAL_STORAGE_PATH)
        if not base.is_absolute():
            from ...db import BASE_DIR

            base = BASE_DIR / base
        serve_url = settings.STORAGE_SERVE_BASE_URL or f"http://{settings.HOST}:{settings.PORT}"
        return LocalFilesystemStorage(
            base_path=base,
            serve_base_url=serve_url,
            sign_secret=settings.JWT_SECRET,
        )

    raise ValueError(f"Неизвестный STORAGE_PROVIDER: {provider!r}. Допустимо: yandex, local")
