"""Вспомогательные эндпоинты ТОЛЬКО для тестовой среды (E2E).

Маршруты этого роутера подключаются в `app/main.py` исключительно когда
`Settings.ENABLE_TEST_ENDPOINTS` истинно (см. переменную окружения
`ENABLE_TEST_ENDPOINTS`). В production роутер не монтируется и недоступен.

Зачем это нужно:
- Фабрика пользователей с заранее заданной ролью и подтверждённым email —
  чтобы E2E-тесты готовили данные через API, а не через UI.
- Чтение «исходящих писем» (in-memory `mailer.outbox`) — чтобы получить
  одноразовый verification/reset token в тестовой среде без реального SMTP.

Никакого влияния на штатную работу приложения: при выключенном флаге модуль
вообще не импортируется в маршруты.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

from .. import mailer, storage
from ..models import UserInDB, UserRole
from ..password_policy import MIN_PASSWORD_LENGTH, validate_password_strength
from ..security import hash_password

router = APIRouter(prefix="/_test", tags=["test-support"])


class CreateTestUserRequest(BaseModel):
    nickname: str = Field(..., min_length=3, max_length=30)
    password: str = Field(default="Password123", min_length=MIN_PASSWORD_LENGTH, max_length=100)
    email: str | None = None
    first_name: str = "Test"
    last_name: str = "User"
    role: UserRole = UserRole.student
    email_verified: bool = True

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        return validate_password_strength(v)


class TestUserOut(BaseModel):
    id: UUID
    nickname: str
    email: str
    role: UserRole
    first_name: str
    last_name: str
    email_verified: bool
    password: str


class OutboxEntry(BaseModel):
    to: str
    subject: str
    token: str
    link: str


@router.post("/users", response_model=TestUserOut, status_code=status.HTTP_201_CREATED)
def create_test_user(payload: CreateTestUserRequest) -> TestUserOut:
    """Создаёт пользователя напрямую (минуя UI-регистрацию) с нужной ролью.

    Удобно для подготовки данных в E2E: можно сразу получить curator/admin и
    подтверждённый email.
    """
    if storage.get_user_by_nickname(payload.nickname) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот никнейм уже занят")

    email = (payload.email or f"{payload.nickname}@example.com").strip().lower()
    if storage.get_user_by_email(email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот email уже зарегистрирован")

    user = UserInDB(
        nickname=payload.nickname,
        role=payload.role,
        hashed_password=hash_password(payload.password),
        email=email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email_verified=payload.email_verified,
    )
    storage.create_user(user)

    return TestUserOut(
        id=user.id,
        nickname=user.nickname,
        email=user.email,
        role=user.role,
        first_name=user.first_name,
        last_name=user.last_name,
        email_verified=user.email_verified,
        password=payload.password,
    )


@router.get("/emails", response_model=list[OutboxEntry])
def list_emails(email: str | None = Query(default=None)) -> list[OutboxEntry]:
    """Список «отправленных» писем (in-memory outbox). Фильтр по получателю."""
    target = email.strip().lower() if email else None
    items = [
        OutboxEntry(**entry)
        for entry in mailer.outbox
        if target is None or entry["to"].strip().lower() == target
    ]
    return items


@router.get("/emails/last", response_model=OutboxEntry)
def last_email(email: str = Query(..., min_length=1)) -> OutboxEntry:
    """Последнее письмо, отправленное на указанный адрес (для verify/reset token)."""
    target = email.strip().lower()
    for entry in reversed(mailer.outbox):
        if entry["to"].strip().lower() == target:
            return OutboxEntry(**entry)
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Письмо для указанного адреса не найдено")
