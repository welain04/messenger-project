"""Локальное файловое хранилище для development (без Yandex)."""

from __future__ import annotations

import hashlib
import hmac
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from .base import SignedUrl, StorageError, StoredObject, StorageService


class LocalFilesystemStorage(StorageService):
    provider_name = "local"

    def __init__(
        self,
        *,
        base_path: Path,
        serve_base_url: str,
        sign_secret: str,
    ) -> None:
        self._base = base_path
        self._base.mkdir(parents=True, exist_ok=True)
        self._serve_base_url = serve_base_url.rstrip("/")
        self._sign_secret = sign_secret

    def _path_for_key(self, key: str) -> Path:
        safe = key.replace("\\", "/").lstrip("/")
        if ".." in safe.split("/"):
            raise StorageError("Недопустимый ключ хранилища")
        return self._base / safe

    def put_object(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        self._log_request("put_object", key=key, content_type=content_type)
        path = self._path_for_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            body = data if isinstance(data, bytes) else data.read()
            path.write_bytes(body)
            result = StoredObject(
                storage_key=key,
                size_bytes=len(body),
                content_type=content_type,
                etag=hashlib.sha256(body).hexdigest()[:32],
                provider=self.provider_name,
            )
            self._log_response("put_object", key=key, size_bytes=len(body))
            return result
        except OSError as exc:
            self._log_error("put_object", exc, key=key)
            raise StorageError("Не удалось записать файл локально", cause=exc) from exc

    def delete_object(self, key: str) -> bool:
        self._log_request("delete_object", key=key)
        path = self._path_for_key(key)
        try:
            if path.is_file():
                path.unlink()
            self._log_response("delete_object", key=key, deleted=True)
            return True
        except OSError as exc:
            self._log_error("delete_object", exc, key=key)
            raise StorageError("Не удалось удалить локальный файл", cause=exc) from exc

    def exists(self, key: str) -> bool:
        self._log_request("exists", key=key)
        exists = self._path_for_key(key).is_file()
        self._log_response("exists", key=key, exists=exists)
        return exists

    def get_presigned_get_url(
        self,
        key: str,
        ttl_seconds: int,
        *,
        filename: str | None = None,
    ) -> SignedUrl:
        self._log_request("get_presigned_get_url", key=key, ttl_seconds=ttl_seconds)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        exp_ts = int(expires_at.timestamp())
        sig = hmac.new(
            self._sign_secret.encode(),
            f"{key}:{exp_ts}".encode(),
            hashlib.sha256,
        ).hexdigest()
        url = (
            f"{self._serve_base_url}/api/v1/files/serve"
            f"?key={quote(key, safe='')}&exp={exp_ts}&sig={sig}"
        )
        if filename:
            url += f"&filename={quote(filename)}"
        self._log_response("get_presigned_get_url", key=key, expires_at=expires_at.isoformat())
        return SignedUrl(url=url, expires_at=expires_at, storage_key=key)

    def copy_object(self, source_key: str, dest_key: str) -> StoredObject:
        self._log_request("copy_object", source_key=source_key, dest_key=dest_key)
        src = self._path_for_key(source_key)
        dst = self._path_for_key(dest_key)
        if not src.is_file():
            raise StorageError("Исходный объект не найден")
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
            body = dst.read_bytes()
            self._log_response("copy_object", dest_key=dest_key, size_bytes=len(body))
            return StoredObject(
                storage_key=dest_key,
                size_bytes=len(body),
                content_type="application/octet-stream",
                provider=self.provider_name,
            )
        except OSError as exc:
            self._log_error("copy_object", exc, source_key=source_key, dest_key=dest_key)
            raise StorageError("Не удалось скопировать локальный файл", cause=exc) from exc

    def read_object(self, key: str) -> tuple[bytes, str]:
        path = self._path_for_key(key)
        if not path.is_file():
            raise StorageError("Объект не найден")
        return path.read_bytes(), "application/octet-stream"
