"""Pydantic-схемы для входа/выхода API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import UserRole

NICKNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


# ----------------------------- Auth / User -----------------------------


class RegisterRequest(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=100)
    role: UserRole

    @field_validator("nickname")
    @classmethod
    def _validate_nickname(cls, v: str) -> str:
        if not NICKNAME_RE.match(v):
            raise ValueError("nickname must contain only letters, digits and underscore")
        return v


class LoginRequest(BaseModel):
    nickname: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nickname: str
    role: UserRole
    created_at: datetime


class UserUpdateRequest(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=30)

    @field_validator("nickname")
    @classmethod
    def _validate_nickname(cls, v: str) -> str:
        if not NICKNAME_RE.match(v):
            raise ValueError("nickname must contain only letters, digits and underscore")
        return v


# ----------------------------- Chats -----------------------------


class ChatCreateRequest(BaseModel):
    type: Literal["personal", "group"]
    title: str | None = Field(default=None, max_length=100)
    participant_ids: list[UUID] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate(self) -> "ChatCreateRequest":
        unique = list({pid for pid in self.participant_ids})
        if len(unique) != len(self.participant_ids):
            raise ValueError("participant_ids must be unique")
        if self.type == "personal":
            if self.title is not None:
                raise ValueError("title is not allowed for personal chats")
        else:
            if not self.title or not self.title.strip():
                raise ValueError("title is required for group chats")
        return self


class ChatBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: Literal["personal", "group"]
    title: str | None
    participant_ids: list[UUID]
    created_by: UUID
    created_at: datetime


class MessagePreview(BaseModel):
    id: UUID
    author_id: UUID
    text: str
    sent_at: datetime


class ChatListItem(ChatBase):
    last_message: MessagePreview | None = None
    unread_count: int = 0


class ChatDetail(ChatBase):
    last_message: MessagePreview | None = None
    unread_count: int = 0


class AddParticipantRequest(BaseModel):
    user_id: UUID


# ----------------------------- Messages -----------------------------


class MessageCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class MessageUpdateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    author_id: UUID
    text: str
    sent_at: datetime
    is_read: bool
    edited_at: datetime | None = None


# ----------------------------- Notifications -----------------------------


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    message: str
    is_read: bool
    created_at: datetime
