"""Редакция чувствительных полей перед записью в лог."""

from __future__ import annotations

from typing import Any

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "hashed_password",
        "refresh_token",
        "access_token",
        "token",
        "authorization",
        "jwt_secret",
        "smtp_password",
        "s3_secret_key",
        "s3_access_key",
        "secret",
        "api_key",
    }
)

_REDACTED = "***"


def mask_email(email: str) -> str:
    if "@" not in email:
        return _REDACTED
    local, domain = email.split("@", 1)
    if not local:
        return f"{_REDACTED}@{domain}"
    return f"{local[0]}{_REDACTED}@{domain}"


def sanitize_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if lowered in _SENSITIVE_KEYS:
        return _REDACTED
    if lowered == "email" and isinstance(value, str):
        return mask_email(value)
    return value


def sanitize_dict(data: dict[str, Any] | None) -> dict[str, Any]:
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out[key] = sanitize_dict(value)
        elif isinstance(value, list):
            out[key] = [
                sanitize_dict(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            out[key] = sanitize_value(key, value)
    return out
