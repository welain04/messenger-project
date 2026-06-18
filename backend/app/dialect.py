"""Единая точка диалект-зависимых деталей БД (SQLite сейчас, PostgreSQL в 6B).

Цель — собрать в одном месте все различия между SQLite и PostgreSQL, чтобы
переход на Postgres (Этап 6B) сводился к правкам здесь, а не по всему storage.py.

Диалект определяется по DATABASE_URL: схема `postgres*` -> postgres, иначе sqlite.
"""

from __future__ import annotations

from .config import get_settings

SQLITE = "sqlite"
POSTGRES = "postgres"


def current_dialect() -> str:
    url = get_settings().DATABASE_URL.strip().lower()
    if url.startswith("postgres"):
        return POSTGRES
    return SQLITE


def is_postgres() -> bool:
    return current_dialect() == POSTGRES


def is_sqlite() -> bool:
    return current_dialect() == SQLITE


def like_operator() -> str:
    """Регистронезависимый поиск.

    SQLite: LIKE регистронезависим для ASCII.
    PostgreSQL: LIKE регистрозависим -> нужен ILIKE.
    """
    return "ILIKE" if is_postgres() else "LIKE"


def to_db_bool(value: bool) -> bool | int:
    """Python bool -> значение для БД (SQLite хранит 0/1, Postgres — boolean)."""
    return value if is_postgres() else int(value)


def from_db_bool(value: object) -> bool:
    """Значение boolean-колонки из БД -> Python bool (универсально)."""
    return bool(value)
