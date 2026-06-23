"""Yandex Object Storage через S3-compatible API (boto3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import BinaryIO

from botocore.exceptions import BotoCoreError, ClientError

from .base import SignedUrl, StorageError, StoredObject, StorageService


class YandexObjectStorage(StorageService):
    provider_name = "yandex"

    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str,
    ) -> None:
        import boto3

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def put_object(
        self,
        key: str,
        data: BinaryIO | bytes,
        content_type: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> StoredObject:
        self._log_request("put_object", key=key, content_type=content_type)
        extra: dict = {"ContentType": content_type}
        if metadata:
            extra["Metadata"] = metadata
        try:
            if isinstance(data, bytes):
                body = data
            else:
                body = data.read()
            size = len(body)
            resp = self._client.put_object(Bucket=self._bucket, Key=key, Body=body, **extra)
            etag = resp.get("ETag", "").strip('"') or None
            result = StoredObject(
                storage_key=key,
                size_bytes=size,
                content_type=content_type,
                etag=etag,
                provider=self.provider_name,
            )
            self._log_response("put_object", key=key, size_bytes=size, etag=etag)
            return result
        except (ClientError, BotoCoreError) as exc:
            self._log_error("put_object", exc, key=key)
            raise StorageError("Не удалось загрузить объект в хранилище", cause=exc) from exc

    def delete_object(self, key: str) -> bool:
        self._log_request("delete_object", key=key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            self._log_response("delete_object", key=key, deleted=True)
            return True
        except (ClientError, BotoCoreError) as exc:
            self._log_error("delete_object", exc, key=key)
            raise StorageError("Не удалось удалить объект", cause=exc) from exc

    def exists(self, key: str) -> bool:
        self._log_request("exists", key=key)
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            self._log_response("exists", key=key, exists=True)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey", "NotFound"):
                self._log_response("exists", key=key, exists=False)
                return False
            self._log_error("exists", exc, key=key)
            raise StorageError("Ошибка проверки объекта", cause=exc) from exc
        except BotoCoreError as exc:
            self._log_error("exists", exc, key=key)
            raise StorageError("Хранилище недоступно", cause=exc) from exc

    def get_presigned_get_url(
        self,
        key: str,
        ttl_seconds: int,
        *,
        filename: str | None = None,
    ) -> SignedUrl:
        self._log_request("get_presigned_get_url", key=key, ttl_seconds=ttl_seconds)
        params: dict = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = f'inline; filename="{filename}"'
        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=ttl_seconds,
            )
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            self._log_response(
                "get_presigned_get_url",
                key=key,
                expires_at=expires_at.isoformat(),
                url_length=len(url),
            )
            return SignedUrl(url=url, expires_at=expires_at, storage_key=key)
        except (ClientError, BotoCoreError) as exc:
            self._log_error("get_presigned_get_url", exc, key=key)
            raise StorageError("Не удалось создать подписанную ссылку", cause=exc) from exc

    def copy_object(self, source_key: str, dest_key: str) -> StoredObject:
        self._log_request("copy_object", source_key=source_key, dest_key=dest_key)
        try:
            self._client.copy_object(
                Bucket=self._bucket,
                Key=dest_key,
                CopySource={"Bucket": self._bucket, "Key": source_key},
            )
            head = self._client.head_object(Bucket=self._bucket, Key=dest_key)
            size = int(head.get("ContentLength", 0))
            content_type = head.get("ContentType", "application/octet-stream")
            etag = head.get("ETag", "").strip('"') or None
            self._log_response("copy_object", dest_key=dest_key, size_bytes=size)
            return StoredObject(
                storage_key=dest_key,
                size_bytes=size,
                content_type=content_type,
                etag=etag,
                provider=self.provider_name,
            )
        except (ClientError, BotoCoreError) as exc:
            self._log_error("copy_object", exc, source_key=source_key, dest_key=dest_key)
            raise StorageError("Не удалось скопировать объект", cause=exc) from exc
