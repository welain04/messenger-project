"""Программный запуск миграций Alembic (используется в db.init_db).

Держим URL единым источником истины (app.config.DATABASE_URL через db.database_url),
переопределяя его в Config поверх значения из alembic.ini.
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

from . import db

BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = BACKEND_DIR / "alembic"


def _config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", db.database_url())
    return cfg


def upgrade_to_head() -> None:
    command.upgrade(_config(), "head")
