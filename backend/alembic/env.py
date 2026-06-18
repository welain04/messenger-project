"""Окружение Alembic.

Миграции пишутся на «сыром» SQL (op.execute / exec_driver_sql), без ORM-моделей,
поэтому target_metadata не задаётся и autogenerate не используется.

URL берётся из секции [alembic] alembic.ini, но на практике он переопределяется
программно (app/alembic_runner.py) значением из app.config.DATABASE_URL.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Чтобы при ручном запуске `alembic` из каталога backend импортировался пакет app.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

config = context.config


def _resolve_url() -> str:
    """URL подключения. Приоритет: env DATABASE_URL -> настройки app -> alembic.ini."""
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    try:
        from app.db import database_url

        return database_url()
    except Exception:  # noqa: BLE001 - офлайн-режим без приложения
        return config.get_main_option("sqlalchemy.url") or "sqlite:///messenger.db"


config.set_main_option("sqlalchemy.url", _resolve_url())


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
