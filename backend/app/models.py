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


ChatType = Literal["personal", "group"]


@dataclass
class UserInDB:
    nickname: str
    role: UserRole
    hashed_password: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_utcnow)


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
    text: str
    id: UUID = field(default_factory=uuid4)
    sent_at: datetime = field(default_factory=_utcnow)
    is_read: bool = False
    edited_at: datetime | None = None


@dataclass
class Notification:
    user_id: UUID
    message: str
    id: UUID = field(default_factory=uuid4)
    is_read: bool = False
    created_at: datetime = field(default_factory=_utcnow)
