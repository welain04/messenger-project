from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from .. import audit, mailer, storage
from ..config import get_settings
from ..deps import get_current_user
from ..models import UserInDB, UserRole
from ..rate_limit import RateLimiter
from ..schemas import (
    LoginRequest,
    LogoutRequest,
    MePrivate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    VerifyEmailRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from ..security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_settings = get_settings()
_login_rate_limit = RateLimiter(_settings.RATE_LIMIT_LOGIN_PER_MIN, 60, "login")
_register_rate_limit = RateLimiter(_settings.RATE_LIMIT_REGISTER_PER_MIN, 60, "register")
_verify_rate_limit = RateLimiter(_settings.RATE_LIMIT_VERIFY_PER_MIN, 60, "verify_email")
_refresh_rate_limit = RateLimiter(_settings.RATE_LIMIT_LOGIN_PER_MIN * 4, 60, "refresh")
_forgot_password_rate_limit = RateLimiter(
    _settings.RATE_LIMIT_FORGOT_PASSWORD_PER_MIN, 60, "forgot_password"
)
_reset_password_rate_limit = RateLimiter(
    _settings.RATE_LIMIT_RESET_PASSWORD_PER_MIN, 60, "reset_password"
)


def _access_token_for(user: UserInDB, sid: UUID) -> str:
    return create_access_token(
        user.id,
        extra={
            "sid": str(sid),
            "role": user.role.value,
            "email_verified": user.email_verified,
            "type": "access",
        },
    )


def _refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=get_settings().REFRESH_TOKEN_EXPIRE_DAYS
    )


def _issue_token_pair(user: UserInDB, request: Request) -> TokenResponse:
    """Создаёт новую сессию (refresh) и access-токен."""
    settings = get_settings()
    raw_refresh = generate_token()
    user_agent = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    sid = storage.create_session(
        user.id, hash_token(raw_refresh), _refresh_expiry(), user_agent, ip
    )
    return TokenResponse(
        access_token=_access_token_for(user, sid),
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def _issue_verification_email(user: UserInDB) -> None:
    """Создаёт токен подтверждения и «отправляет» письмо."""
    settings = get_settings()
    raw = generate_token()
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.EMAIL_VERIFICATION_TTL_HOURS
    )
    storage.create_email_verification_token(user.id, user.email, hash_token(raw), expires)
    mailer.send_verification_email(user.email, raw)


@router.post(
    "/register",
    response_model=MePrivate,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_register_rate_limit)],
)
def register(payload: RegisterRequest) -> MePrivate:
    if not get_settings().ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Регистрация закрыта. Обратитесь к администратору",
        )
    if storage.get_user_by_nickname(payload.nickname) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот никнейм уже занят")
    if storage.get_user_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Этот email уже зарегистрирован")

    user = UserInDB(
        nickname=payload.nickname,
        role=UserRole.student,
        hashed_password=hash_password(payload.password),
        email=str(payload.email),
        first_name=payload.first_name,
        last_name=payload.last_name,
        email_verified=False,
    )
    storage.create_user(user)
    _issue_verification_email(user)
    audit.record(
        "auth.register",
        "user",
        actor_id=user.id,
        entity_id=user.id,
        data={"nickname": user.nickname, "email": user.email},
    )
    return MePrivate.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(_login_rate_limit)],
)
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    ip = request.client.host if request.client else None
    user = storage.get_user_by_nickname(payload.nickname)
    if not user or not verify_password(payload.password, user.hashed_password):
        audit.record(
            "auth.login_failed",
            "user",
            data={"nickname": payload.nickname, "ip": ip},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный никнейм или пароль")
    if not user.is_active:
        audit.record(
            "auth.login_failed", "user", actor_id=user.id,
            data={"reason": "suspended", "ip": ip},
        )
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Аккаунт заблокирован. Обратитесь к администратору",
        )

    pair = _issue_token_pair(user, request)
    audit.record("auth.login", "user", actor_id=user.id, data={"ip": ip})
    return pair


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(_refresh_rate_limit)],
)
def refresh(payload: RefreshRequest, request: Request) -> TokenResponse:
    settings = get_settings()
    token_hash = hash_token(payload.refresh_token)
    session = storage.get_active_session_by_refresh(token_hash)
    if session is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Сессия недействительна. Войдите снова",
        )

    user = storage.get_user(UUID(session["user_id"]))
    if user is None or not user.is_active:
        storage.revoke_session(session["id"])
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Сессия недействительна. Войдите снова",
        )

    # Ротация refresh-токена: старый перестаёт действовать.
    new_refresh = generate_token()
    storage.rotate_session(session["id"], hash_token(new_refresh), _refresh_expiry())
    return TokenResponse(
        access_token=_access_token_for(user, UUID(str(session["id"]))),
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, request: Request) -> None:
    # Отзываем сессию по refresh-токену; если его нет — по sid из access-токена.
    actor = getattr(request.state, "user", None)
    actor_id = actor.id if actor else None
    if payload.refresh_token:
        storage.revoke_session_by_refresh(hash_token(payload.refresh_token))
    else:
        sid = getattr(request.state, "sid", None)
        if sid:
            storage.revoke_session(sid)
    audit.record("auth.logout", "session", actor_id=actor_id)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(current: UserInDB = Depends(get_current_user)) -> None:
    storage.revoke_all_sessions(current.id)
    audit.record("auth.logout_all", "session", actor_id=current.id)


@router.post(
    "/verify-email",
    response_model=MePrivate,
    dependencies=[Depends(_verify_rate_limit)],
)
def verify_email(payload: VerifyEmailRequest) -> MePrivate:
    row = storage.get_active_email_token(hash_token(payload.token))
    if row is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ссылка подтверждения недействительна или устарела",
        )

    user_id = UUID(row["user_id"])
    storage.consume_email_token(row["id"])
    storage.mark_email_verified(user_id)
    audit.record("auth.email_verified", "user", actor_id=user_id, entity_id=user_id)

    user = storage.get_user(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    return MePrivate.model_validate(user)


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
def resend_verification(current: UserInDB = Depends(get_current_user)) -> dict[str, str]:
    settings = get_settings()

    if current.email_verified:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email уже подтверждён")

    now = datetime.now(timezone.utc)

    last = storage.last_email_token_created_at(current.id)
    if last is not None:
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (now - last).total_seconds()
        if elapsed < settings.EMAIL_RESEND_COOLDOWN_SECONDS:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Письмо уже отправлено. Повторите запрос чуть позже",
            )

    day_ago = now - timedelta(days=1)
    if storage.count_email_tokens_since(current.id, day_ago) >= settings.EMAIL_RESEND_MAX_PER_DAY:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Превышен суточный лимит писем подтверждения",
        )

    _issue_verification_email(current)
    return {"detail": "Письмо отправлено"}


def _issue_password_reset_email(user: UserInDB) -> None:
    settings = get_settings()
    raw = generate_token()
    expires = datetime.now(timezone.utc) + timedelta(
        hours=settings.PASSWORD_RESET_TTL_HOURS
    )
    storage.create_password_reset_token(user.id, hash_token(raw), expires)
    mailer.send_password_reset_email(user.email, raw)


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(_forgot_password_rate_limit)],
)
def forgot_password(payload: ForgotPasswordRequest) -> dict[str, str]:
    """Запрос ссылки для сброса пароля. Всегда возвращает 202 (не раскрывает наличие email)."""
    settings = get_settings()
    email = str(payload.email).strip().lower()
    user = storage.get_user_by_email(email)

    if user is not None and user.is_active:
        now = datetime.now(timezone.utc)
        last = storage.last_password_reset_token_created_at(user.id)
        if last is not None:
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            elapsed = (now - last).total_seconds()
            if elapsed < settings.PASSWORD_RESET_COOLDOWN_SECONDS:
                return {"detail": "Если аккаунт существует, письмо уже отправлено"}
        day_ago = now - timedelta(days=1)
        if storage.count_password_reset_tokens_since(user.id, day_ago) >= settings.PASSWORD_RESET_MAX_PER_DAY:
            return {"detail": "Если аккаунт существует, письмо уже отправлено"}
        _issue_password_reset_email(user)
        audit.record(
            "auth.password_reset_requested",
            "user",
            actor_id=user.id,
            entity_id=user.id,
        )

    return {"detail": "Если аккаунт существует, на email отправлена ссылка для сброса пароля"}


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_reset_password_rate_limit)],
)
def reset_password(payload: ResetPasswordRequest) -> None:
    row = storage.get_active_password_reset_token(hash_token(payload.token))
    if row is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ссылка для сброса пароля недействительна или устарела",
        )

    user_id = UUID(row["user_id"])
    user = storage.get_user(user_id)
    if user is None or not user.is_active:
        storage.consume_password_reset_token(row["id"])
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ссылка для сброса пароля недействительна или устарела",
        )

    storage.consume_password_reset_token(row["id"])
    storage.update_password(user_id, hash_password(payload.new_password))
    storage.revoke_all_sessions(user_id)
    audit.record("auth.password_reset", "user", actor_id=user_id, entity_id=user_id)
