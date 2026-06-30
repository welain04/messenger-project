"""Оркестрация файлов: валидация, storage, БД."""

from __future__ import annotations

import hashlib
import logging
import mimetypes
import re
from datetime import datetime, timedelta, timezone
from typing import BinaryIO
from uuid import UUID, uuid4

import filetype
from fastapi import HTTPException, UploadFile, status

from .. import storage as db_storage
from ..config import Settings, get_settings
from ..models import Attachment, Message, StagedUpload, UserInDB
from .storage.base import SignedUrl, StorageError, StorageService

logger = logging.getLogger("messenger.files")

AttachmentKind = str

# Текстовые форматы без устойчивой бинарной сигнатуры — filetype их не
# определяет, поэтому для них (и только если тип в allowlist) доверяем
# заявленному Content-Type.
_SNIFF_EXEMPT_MIMES = {"text/plain"}


class FileService:
    def __init__(self, storage_svc: StorageService, settings: Settings | None = None) -> None:
        self._storage = storage_svc
        self._settings = settings or get_settings()

    # --------------------------- safe helpers (non-blocking) ---------------------------

    def safe_delete(self, key: str | None) -> None:
        """Удаление объекта: ошибка логируется, основное действие не блокируется."""
        if not key:
            return
        try:
            self._storage.delete_object(key)
        except StorageError as exc:
            logger.warning("safe_delete failed key=%s error=%s", key, exc, exc_info=True)

    def safe_presign(
        self,
        key: str | None,
        *,
        filename: str | None = None,
    ) -> SignedUrl | None:
        """Presigned URL: при ошибке хранилища возвращает None."""
        if not key:
            return None
        try:
            return self._storage.get_presigned_get_url(
                key,
                self._settings.SIGNED_URL_TTL_SECONDS,
                filename=filename,
            )
        except StorageError as exc:
            logger.warning("safe_presign failed key=%s error=%s", key, exc, exc_info=True)
            return None

    # --------------------------- validation ---------------------------

    def _read_upload(self, file: UploadFile, max_bytes: int) -> tuple[bytes, str]:
        content_type = (file.content_type or "application/octet-stream").split(";")[0].strip()
        data = file.file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"Файл слишком большой (макс. {max_bytes // (1024 * 1024)} МБ)",
            )
        return data, content_type

    def _check_mime(self, content_type: str, allowed: list[str]) -> None:
        for pattern in allowed:
            if pattern.endswith("/*"):
                prefix = pattern[:-1]
                if content_type.startswith(prefix):
                    return
            elif content_type == pattern:
                return
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Недопустимый тип файла")

    def _resolve_content_type(self, data: bytes, declared: str, allowed: list[str]) -> str:
        """Определяет реальный MIME по содержимому (magic bytes) и сверяет с allowlist.

        Возвращает фактический content-type для хранения. Заявленному клиентом
        Content-Type доверяем только для текстовых форматов без сигнатуры
        (см. _SNIFF_EXEMPT_MIMES), чтобы нельзя было замаскировать бинарь под
        разрешённый тип.
        """
        kind = filetype.guess(data)
        sniffed = kind.mime if kind else None
        if sniffed is not None:
            self._check_mime(sniffed, allowed)
            return sniffed
        # Сигнатура не распознана: допускаем лишь заявленный текстовый тип,
        # дополнительно отсекая бинарные данные по NUL-байту.
        if declared in _SNIFF_EXEMPT_MIMES and b"\x00" not in data:
            self._check_mime(declared, allowed)
            return declared
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Недопустимый тип файла")

    def _checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _avatar_ext(self, content_type: str) -> str:
        ext = mimetypes.guess_extension(content_type) or ".bin"
        return ext.replace("jpeg", "jpg") if ext == ".jpe" else ext

    def _attachment_kind(self, content_type: str) -> AttachmentKind:
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("video/"):
            return "video"
        if content_type.startswith("audio/"):
            return "audio"
        return "file"

    # --------------------------- avatars ---------------------------

    def upload_avatar(self, user: UserInDB, file: UploadFile) -> UserInDB:
        data, declared = self._read_upload(file, self._settings.AVATAR_MAX_BYTES)
        content_type = self._resolve_content_type(
            data, declared, self._settings.allowed_avatar_mimes_list
        )

        ext = self._avatar_ext(content_type)
        key = f"avatars/{user.id}/{uuid4()}{ext}"
        old_key = db_storage.get_avatar_key(user.id)

        try:
            self._storage.put_object(key, data, content_type)
        except StorageError as exc:
            logger.error("avatar upload storage failed user=%s key=%s", user.id, key, exc_info=True)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Хранилище временно недоступно. Попробуйте позже",
            ) from exc

        db_storage.set_avatar_key(user.id, key)
        user.avatar_url = key
        self.safe_delete(old_key)
        return user

    def delete_avatar(self, user: UserInDB) -> UserInDB:
        old_key = db_storage.get_avatar_key(user.id)
        db_storage.set_avatar_key(user.id, None)
        user.avatar_url = None
        self.safe_delete(old_key)
        return user

    def get_avatar_signed_url(
        self,
        target_user_id: UUID,
        viewer: UserInDB,
    ) -> SignedUrl | None:
        if not db_storage.can_view_avatar(target_user_id, viewer.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к аватару")
        key = db_storage.get_avatar_key(target_user_id)
        return self.safe_presign(key)

    # --------------------------- staged uploads ---------------------------

    def stage_upload(self, user: UserInDB, file: UploadFile) -> StagedUpload:
        data, declared = self._read_upload(file, self._settings.ATTACHMENT_MAX_BYTES)
        content_type = self._resolve_content_type(
            data, declared, self._settings.allowed_attachment_mimes_list
        )

        upload_id = uuid4()
        key = f"staging/{user.id}/{upload_id}"
        kind = self._attachment_kind(content_type)
        checksum = self._checksum(data)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self._settings.STAGING_TTL_HOURS)

        try:
            stored = self._storage.put_object(key, data, content_type)
        except StorageError as exc:
            logger.error("stage upload storage failed user=%s", user.id, exc_info=True)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Хранилище временно недоступно. Попробуйте позже",
            ) from exc

        staged = StagedUpload(
            id=upload_id,
            uploader_id=user.id,
            storage_key=key,
            kind=kind,
            file_name=file.filename or "file",
            mime_type=content_type,
            size_bytes=stored.size_bytes,
            checksum=checksum,
            expires_at=expires_at,
        )
        db_storage.create_staged_upload(staged)
        return staged

    def cancel_staged_upload(self, upload_id: UUID, user: UserInDB) -> None:
        staged = db_storage.get_staged_upload(upload_id)
        if not staged or staged.uploader_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Загрузка не найдена")
        if staged.consumed_at:
            return
        db_storage.mark_staged_upload_consumed(upload_id)
        self.safe_delete(staged.storage_key)

    # --------------------------- messages + attachments ---------------------------

    def _final_attachment_key(self, chat_id: UUID, upload_id: UUID) -> str:
        now = datetime.now(timezone.utc)
        return f"attachments/{chat_id}/{now:%Y/%m}/{upload_id}"

    def create_message_with_attachments(
        self,
        chat_id: UUID,
        author: UserInDB,
        text: str | None,
        upload_ids: list[UUID],
    ) -> tuple[Message, list[Attachment]]:
        text_norm = (text or "").strip()
        if not text_norm and not upload_ids:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Укажите текст или прикрепите файл",
            )
        if text_norm and len(text_norm) > 2000:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Текст сообщения слишком длинный")

        msg = Message(chat_id=chat_id, author_id=author.id, text=text_norm)
        attachments: list[Attachment] = []

        staged_list: list[StagedUpload] = []
        for uid in upload_ids:
            staged = db_storage.get_staged_upload(uid)
            if not staged or staged.uploader_id != author.id:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Нельзя использовать чужие или неизвестные вложения",
                )
            if staged.consumed_at:
                raise HTTPException(status.HTTP_410_GONE, "Срок загрузки истёк, прикрепите файл снова")
            if staged.expires_at < datetime.now(timezone.utc):
                raise HTTPException(status.HTTP_410_GONE, "Срок загрузки истёк, прикрепите файл снова")
            staged_list.append(staged)

        db_storage.create_message(msg, body=text_norm or None)

        for staged in staged_list:
            dest_key = self._final_attachment_key(chat_id, staged.id)
            final_key = staged.storage_key
            try:
                copied = self._storage.copy_object(staged.storage_key, dest_key)
                final_key = copied.storage_key
                self.safe_delete(staged.storage_key)
            except StorageError as exc:
                logger.warning(
                    "copy to attachments failed, keeping staging key upload=%s error=%s",
                    staged.id,
                    exc,
                )
                final_key = staged.storage_key

            att = Attachment(
                message_id=msg.id,
                kind=staged.kind,
                storage_key=final_key,
                file_name=staged.file_name,
                mime_type=staged.mime_type,
                size_bytes=staged.size_bytes,
                checksum=staged.checksum,
            )
            db_storage.create_attachment(att)
            db_storage.mark_staged_upload_consumed(staged.id, message_id=msg.id)
            attachments.append(att)

        return msg, attachments

    def get_attachment_signed_url(
        self,
        attachment_id: UUID,
        viewer: UserInDB,
    ) -> SignedUrl | None:
        att = db_storage.get_attachment(attachment_id)
        if not att:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Вложение не найдено")
        msg = db_storage.get_message(att.message_id)
        if not msg:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Сообщение не найдено")
        if not db_storage.is_participant(msg.chat_id, viewer.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к файлу")
        return self.safe_presign(att.storage_key, filename=att.file_name)

    def attachments_for_messages(self, message_ids: list[UUID]) -> dict[UUID, list[Attachment]]:
        return db_storage.list_attachments_for_messages(message_ids)

    def verify_local_serve_token(self, key: str, exp: int, sig: str) -> bool:
        import hmac as hm

        expected = hm.new(
            self._settings.JWT_SECRET.encode(),
            f"{key}:{exp}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hm.compare_digest(expected, sig):
            return False
        if datetime.now(timezone.utc).timestamp() > exp:
            return False
        return True
