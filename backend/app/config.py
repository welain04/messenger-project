from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Значения JWT_SECRET, недопустимые в production (дефолты из репозитория).
_INSECURE_SECRETS = {
    "",
    "change-me",
    "change-me-please-super-secret-key",
}


class Settings(BaseSettings):
    """Конфигурация приложения, читаемая из переменных окружения / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # development | production. В production запрещён небезопасный JWT_SECRET.
    APP_ENV: str = "development"

    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Путь к файлу SQLite. Пусто -> backend/messenger.db (см. app/db.py).
    DATABASE_PATH: str = ""

    # URL подключения к БД для Alembic и будущего PostgreSQL (Этап 6B).
    # Пусто -> SQLite по DATABASE_PATH (или backend/messenger.db).
    # Пример PostgreSQL: postgresql+psycopg://user:pass@localhost:5432/messenger
    DATABASE_URL: str = ""

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Rate limiting (запросов в минуту на один IP). 0 -> лимит отключён.
    RATE_LIMIT_LOGIN_PER_MIN: int = 5
    RATE_LIMIT_REGISTER_PER_MIN: int = 5
    RATE_LIMIT_SEARCH_PER_MIN: int = 30
    RATE_LIMIT_VERIFY_PER_MIN: int = 10
    RATE_LIMIT_FORGOT_PASSWORD_PER_MIN: int = 3

    # Подтверждение email.
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    EMAIL_VERIFICATION_TTL_HOURS: int = 24
    EMAIL_RESEND_COOLDOWN_SECONDS: int = 60
    EMAIL_RESEND_MAX_PER_DAY: int = 5

    # Сброс пароля по email.
    PASSWORD_RESET_TTL_HOURS: int = 1
    PASSWORD_RESET_COOLDOWN_SECONDS: int = 60
    PASSWORD_RESET_MAX_PER_DAY: int = 5

    # SMTP (если пусто -> письма логируются в консоль, dev-режим).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@example.com"
    # SSL-подключение (порт 465). Если False — STARTTLS (порт 587).
    # Для порта 465 SSL включается автоматически.
    SMTP_USE_SSL: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Object storage (Yandex Object Storage / local dev).
    STORAGE_PROVIDER: str = "local"
    S3_ENDPOINT: str = "https://storage.yandexcloud.net"
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "ru-central1"
    SIGNED_URL_TTL_SECONDS: int = 120
    AVATAR_MAX_BYTES: int = 5 * 1024 * 1024
    ATTACHMENT_MAX_BYTES: int = 20 * 1024 * 1024
    ALLOWED_AVATAR_MIMES: str = "image/jpeg,image/png,image/webp"
    ALLOWED_ATTACHMENT_MIMES: str = (
        "image/jpeg,image/png,image/webp,image/gif,"
        "application/pdf,text/plain,application/zip"
    )
    STAGING_TTL_HOURS: int = 24
    LOCAL_STORAGE_PATH: str = "uploads"
    # Базовый URL для presigned-ссылок local-провайдера (пусто -> http://HOST:PORT).
    STORAGE_SERVE_BASE_URL: str = ""

    @property
    def allowed_avatar_mimes_list(self) -> list[str]:
        return [m.strip() for m in self.ALLOWED_AVATAR_MIMES.split(",") if m.strip()]

    @property
    def allowed_attachment_mimes_list(self) -> list[str]:
        return [m.strip() for m in self.ALLOWED_ATTACHMENT_MIMES.split(",") if m.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.strip().lower() == "production"

    @model_validator(mode="after")
    def _enforce_secret(self) -> "Settings":
        if self.is_production and self.JWT_SECRET in _INSECURE_SECRETS:
            raise ValueError(
                "В production необходимо задать надёжный JWT_SECRET в .env "
                "(текущее значение является небезопасным значением по умолчанию)."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
