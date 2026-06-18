"""Подключение к SQLite и низкоуровневые помощники доступа к данным.

Одно соединение на процесс (check_same_thread=False) + RLock, т.к. FastAPI
выполняет sync-эндпоинты в пуле потоков. Для SQLite этого достаточно.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Sequence

from .config import get_settings
from .migrations import run_migrations

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

lock = RLock()
_conn: sqlite3.Connection | None = None


def _db_path() -> str:
    settings = get_settings()
    if settings.DATABASE_PATH:
        return settings.DATABASE_PATH
    return str(BASE_DIR / "messenger.db")


def database_url() -> str:
    """URL подключения для Alembic/SQLAlchemy.

    Приоритет: явный DATABASE_URL -> SQLite по DATABASE_PATH/умолчанию.
    """
    settings = get_settings()
    if settings.DATABASE_URL.strip():
        return settings.DATABASE_URL.strip()
    return f"sqlite:///{_db_path()}"


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        with lock:
            if _conn is None:
                conn = sqlite3.connect(_db_path(), check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA foreign_keys=ON;")
                _conn = conn
    return _conn


def init_db() -> None:
    """Применяет миграции Alembic до последней версии (идемпотентно).

    Baseline-миграция повторяет schema.sql (CREATE ... IF NOT EXISTS), поэтому
    безопасна и для пустой, и для уже существующей базы. Для старых SQLite-баз,
    созданных до Alembic, дополнительно прогоняем легаси ADD COLUMN-миграции.
    """
    from . import dialect
    from .alembic_runner import upgrade_to_head

    upgrade_to_head()

    if dialect.is_sqlite():
        conn = get_connection()
        with lock:
            run_migrations(conn)
            conn.commit()


def close_connection() -> None:
    global _conn
    with lock:
        if _conn is not None:
            _conn.close()
            _conn = None


# --------------------------- helpers ---------------------------


def query_all(sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    conn = get_connection()
    with lock:
        return conn.execute(sql, params).fetchall()


def query_one(sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    conn = get_connection()
    with lock:
        return conn.execute(sql, params).fetchone()


def execute(sql: str, params: Sequence[Any] = ()) -> int:
    """Выполнить запись и зафиксировать. Возвращает rowcount."""
    conn = get_connection()
    with lock:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.rowcount


def execute_script(statements: Iterable[tuple[str, Sequence[Any]]]) -> None:
    """Выполнить несколько запросов в одной транзакции."""
    conn = get_connection()
    with lock:
        try:
            for sql, params in statements:
                conn.execute(sql, params)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
