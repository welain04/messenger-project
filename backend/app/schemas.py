"""Pydantic-схемы для входа/выхода API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from .models import UserRole
from .password_policy import MIN_PASSWORD_LENGTH, validate_password_strength

NICKNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
# Имя/фамилия: буквы (лат./кир.), пробел, дефис, апостроф.
NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё '\-]*$")

# Зарезервированные никнеймы (нельзя занять при регистрации/смене).
RESERVED_NICKNAMES = {
    "admin", "administrator", "root", "system", "support",
    "moderator", "curator", "me", "null", "undefined",
}


def _validate_nickname_value(v: str) -> str:
    if not NICKNAME_RE.match(v):
        raise ValueError("Никнейм: только латинские буквы, цифры и символ _")
    if v.lower() in RESERVED_NICKNAMES:
        raise ValueError("Этот никнейм зарезервирован")
    return v


def _validate_name_value(v: str, field_label: str) -> str:
    v = v.strip()
    if not NAME_RE.match(v):
        raise ValueError(f"{field_label}: только буквы, пробел, дефис и апостроф")
    return v


# ----------------------------- Auth / User -----------------------------


class RegisterRequest(BaseModel):
    # Роль НЕ принимается от клиента: все новые пользователи — student.
    # Повышение до curator/admin выполняется только через админский флоу.
    nickname: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=100)
    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("nickname")
    @classmethod
    def _validate_nickname(cls, v: str) -> str:
        return _validate_nickname_value(v)

    @field_validator("first_name")
    @classmethod
    def _validate_first_name(cls, v: str) -> str:
        return _validate_name_value(v, "Имя")

    @field_validator("last_name")
    @classmethod
    def _validate_last_name(cls, v: str) -> str:
        return _validate_name_value(v, "Фамилия")


class LoginRequest(BaseModel):
    nickname: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # время жизни access-токена в секундах


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class SessionOut(BaseModel):
    id: UUID
    user_agent: str | None = None
    ip: str | None = None
    created_at: datetime
    last_seen_at: datetime
    current: bool = False


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=100)

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH, max_length=100)

    @field_validator("new_password")
    @classmethod
    def _validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)


class UserPublic(BaseModel):
    """Публичная карточка пользователя (видна другим). Без email."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nickname: str
    role: UserRole
    first_name: str
    last_name: str
    created_at: datetime
    has_avatar: bool = False


class MePrivate(UserPublic):
    """Данные о себе — дополнительно содержат приватные поля."""

    email: str
    email_verified: bool


class UserUpdateRequest(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=30)

    @field_validator("nickname")
    @classmethod
    def _validate_nickname(cls, v: str) -> str:
        return _validate_nickname_value(v)


# ----------------------------- Admin -----------------------------


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    nickname: str
    role: UserRole
    is_active: bool
    created_at: datetime


class RoleUpdateRequest(BaseModel):
    role: UserRole


class RoleUpgradeCreate(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RoleUpgradeReview(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class RoleUpgradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    requested_role: UserRole
    status: Literal["pending", "approved", "rejected"]
    reason: str | None = None
    reviewed_by: UUID | None = None
    review_note: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None


class AuditLogOut(BaseModel):
    id: UUID
    actor_id: UUID | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    data: dict = Field(default_factory=dict)
    created_at: datetime


# ----------------------------- Chats -----------------------------


class ChatCreateRequest(BaseModel):
    type: Literal["personal", "group"]
    title: str | None = Field(default=None, max_length=100)
    participant_ids: list[UUID] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _validate(self) -> "ChatCreateRequest":
        unique = list({pid for pid in self.participant_ids})
        if len(unique) != len(self.participant_ids):
            raise ValueError("Список участников не должен содержать дубликаты")
        if self.type == "personal":
            if self.title is not None:
                raise ValueError("Для личного чата название не указывается")
        else:
            if not self.title or not self.title.strip():
                raise ValueError("Для группового чата укажите название")
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


# ----------------------------- Files / Attachments -----------------------------


class SignedUrlOut(BaseModel):
    url: str
    expires_at: datetime
    storage_key: str


class StagedUploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: Literal["image", "video", "audio", "file"]
    file_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    expires_at: datetime


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    message_id: UUID
    kind: Literal["image", "video", "audio", "file"]
    file_name: str | None
    mime_type: str | None
    size_bytes: int | None
    created_at: datetime


# ----------------------------- Messages -----------------------------


class MessageCreateRequest(BaseModel):
    text: str | None = Field(default=None, max_length=2000)
    upload_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_content(self) -> "MessageCreateRequest":
        text_ok = self.text is not None and self.text.strip()
        if not text_ok and not self.upload_ids:
            raise ValueError("Укажите текст или прикрепите файл")
        return self


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
    attachments: list[AttachmentOut] = Field(default_factory=list)


# ----------------------------- Notifications -----------------------------


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    message: str
    is_read: bool
    created_at: datetime
