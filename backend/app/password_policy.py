"""Единые правила сложности пароля для API."""

from __future__ import annotations

import re

MIN_PASSWORD_LENGTH = 8

_HAS_LETTER = re.compile(r"[A-Za-z]")
_HAS_DIGIT = re.compile(r"\d")


def validate_password_strength(password: str) -> str:
    """Проверяет пароль и возвращает его же; при нарушении — ValueError с русским текстом."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Пароль: минимум {MIN_PASSWORD_LENGTH} символов")
    if not _HAS_LETTER.search(password):
        raise ValueError("Пароль: должен содержать хотя бы одну букву")
    if not _HAS_DIGIT.search(password):
        raise ValueError("Пароль: должен содержать хотя бы одну цифру")
    return password
