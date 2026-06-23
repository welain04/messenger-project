"""Внутренние in-memory модели (не путать с Pydantic-схемами для API)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, Enum):
    student = "student"
    curator = "curator"
    admin = "admin"


ChatType = Literal["personal", "group"]


@dataclass
class UserInDB:
    nickname: str
    role: UserRole
    hashed_password: str
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    email_verified: bool = False
    avatar_url: str | None = None  # storage_key в Object Storage
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    is_active: bool = True

    @property
    def has_avatar(self) -> bool:
        return bool(self.avatar_url)


@dataclass
class Chat:
    type: ChatType
    participant_ids: list[UUID]
    created_by: UUID
    title: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class Message:
    chat_id: UUID
    author_id: UUID
    text: str = ""
    id: UUID = field(default_factory=uuid4)
    sent_at: datetime = field(default_factory=_utcnow)
    is_read: bool = False
    edited_at: datetime | None = None
    attachments: list["Attachment"] = field(default_factory=list)


AttachmentKind = Literal["image", "video", "audio", "file"]


@dataclass
class Attachment:
    message_id: UUID
    kind: AttachmentKind
    storage_key: str
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)


@dataclass
class StagedUpload:
    uploader_id: UUID
    storage_key: str
    kind: AttachmentKind
    file_name: str
    mime_type: str
    size_bytes: int
    checksum: str
    expires_at: datetime
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)
    consumed_at: datetime | None = None
    message_id: UUID | None = None


@dataclass
class Notification:
    user_id: UUID
    message: str
    id: UUID = field(default_factory=uuid4)
    is_read: bool = False
    created_at: datetime = field(default_factory=_utcnow)
    actor_id: UUID | None = None
    chat_id: UUID | None = None
    message_id: UUID | None = None
