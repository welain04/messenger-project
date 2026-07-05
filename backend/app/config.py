import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Значения JWT_SECRET, недопустимые в production (дефолты из репозитория).
_INSECURE_SECRETS = {
    "",
    "change-me",
    "change-me-please-super-secret-key",
}

# Подстроки, недопустимые в публичных URL production-конфигурации.
_LOCAL_HOST_MARKERS = ("localhost", "127.0.0.1")


class Settings(BaseSettings):
    """Конфигурация приложения, читаемая из переменных окружения / .env."""

    # По умолчанию читаем .env. Для тестовой среды можно указать другой файл
    # через переменную ENV_FILE (например, ENV_FILE=.env.test). Явные
    # переменные окружения всё равно имеют приоритет над файлом.
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # development | production. В production запрещён небезопасный JWT_SECRET.
    APP_ENV: str = "development"

    # Включает вспомогательные тестовые эндпоинты (/api/v1/_test/*) для E2E.
    # ВНИМАНИЕ: только для тестовой среды. В production должно быть False.
    ENABLE_TEST_ENDPOINTS: bool = False

    # Открытая регистрация новых пользователей (роль student).
    # false -> POST /auth/register возвращает 403 (invite-only / закрытая школа).
    ALLOW_PUBLIC_REGISTRATION: bool = True

    # Security headers (X-Frame-Options, X-Content-Type-Options и др.).
    # По умолчанию включены в production; в development можно включить явно.
    ENABLE_SECURITY_HEADERS: bool = False

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

    # За обратным прокси (nginx и т.п.) реальный IP клиента приходит в
    # X-Forwarded-For. Доверять заголовку можно ТОЛЬКО когда приложение
    # действительно стоит за доверенным прокси, иначе клиент подделает IP и
    # обойдёт rate limit. По умолчанию выключено (используется прямой peer IP).
    TRUST_PROXY_HEADERS: bool = False
    # Число доверенных прокси перед приложением (1 = только nginx).
    TRUSTED_PROXY_COUNT: int = 1

    # Rate limiting (запросов в минуту на один IP). 0 -> лимит отключён.
    RATE_LIMIT_LOGIN_PER_MIN: int = 5
    RATE_LIMIT_REGISTER_PER_MIN: int = 5
    RATE_LIMIT_SEARCH_PER_MIN: int = 30
    RATE_LIMIT_VERIFY_PER_MIN: int = 10
    RATE_LIMIT_FORGOT_PASSWORD_PER_MIN: int = 3
    RATE_LIMIT_RESET_PASSWORD_PER_MIN: int = 10

    # Rate limit: memory (один процесс) | redis (заготовка для нескольких инстансов).
    RATE_LIMIT_BACKEND: str = "memory"
    REDIS_URL: str = ""

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

    # Sentry (пустой DSN -> отключено).
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0
    # Ключ для GET /health/sentry-test?key=... (пусто -> эндпоинт не регистрируется).
    SENTRY_DEBUG_KEY: str = ""

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

    @property
    def security_headers_enabled(self) -> bool:
        return self.is_production or self.ENABLE_SECURITY_HEADERS

    @staticmethod
    def _contains_local_host(value: str) -> bool:
        lowered = value.strip().lower()
        return any(marker in lowered for marker in _LOCAL_HOST_MARKERS)

    @model_validator(mode="after")
    def _enforce_production_rules(self) -> "Settings":
        if not self.is_production:
            return self

        if self.JWT_SECRET in _INSECURE_SECRETS:
            raise ValueError(
                "В production необходимо задать надёжный JWT_SECRET в .env "
                "(текущее значение является небезопасным значением по умолчанию)."
            )
        if self.ENABLE_TEST_ENDPOINTS:
            raise ValueError(
                "В production тестовые эндпоинты должны быть выключены: "
                "установите ENABLE_TEST_ENDPOINTS=false."
            )
        if not self.SMTP_HOST.strip():
            raise ValueError(
                "В production необходимо задать SMTP_HOST — иначе письма "
                "подтверждения email и сброса пароля не дойдут до пользователей."
            )
        if self.STORAGE_PROVIDER.strip().lower() == "local":
            raise ValueError(
                "В production STORAGE_PROVIDER не может быть local — "
                "используйте yandex (или другой S3-совместимый провайдер)."
            )
        provider = self.STORAGE_PROVIDER.strip().lower()
        if provider == "yandex":
            missing = [
                name
                for name, value in (
                    ("S3_BUCKET", self.S3_BUCKET),
                    ("S3_ACCESS_KEY", self.S3_ACCESS_KEY),
                    ("S3_SECRET_KEY", self.S3_SECRET_KEY),
                )
                if not value.strip()
            ]
            if missing:
                raise ValueError(
                    "В production при STORAGE_PROVIDER=yandex необходимо задать: "
                    + ", ".join(missing)
                )
        if self._contains_local_host(self.FRONTEND_BASE_URL):
            raise ValueError(
                "В production FRONTEND_BASE_URL не должен указывать на localhost "
                "или 127.0.0.1 — задайте публичный URL фронтенда."
            )
        if not self.cors_origins_list:
            raise ValueError(
                "В production CORS_ORIGINS не может быть пустым — "
                "укажите публичные origin'ы фронтенда через запятую."
            )
        for origin in self.cors_origins_list:
            if self._contains_local_host(origin):
                raise ValueError(
                    f"В production CORS_ORIGINS не должен содержать localhost "
                    f"или 127.0.0.1 (проблемный origin: {origin!r})."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
