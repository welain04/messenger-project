"""baseline: исходная схема (снимок app/schema.sql)

Baseline-миграция Этапа 6A. Создаёт всю текущую схему из app/schema.sql.
Все выражения там — CREATE TABLE/INDEX IF NOT EXISTS, поэтому миграция
идемпотентна и безопасна как для пустой БД, так и для уже существующей
(созданной старым init_db) — её достаточно «накатить» поверх.

Дальнейшие изменения схемы оформляются НОВЫМИ ревизиями Alembic, а не правкой
schema.sql (он остаётся снимком v1 для справки).

Revision ID: 0001_initial
Revises:
"""

from __future__ import annotations

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "app" / "schema.sql"


def _statements(sql_text: str):
    """Разбить schema.sql на отдельные SQL-выражения.

    Убираем строки-комментарии (`-- ...`), затем делим по `;`. В схеме нет
    точек с запятой и двоеточий внутри выражений, поэтому такого разбора хватает.
    """
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    joined = "\n".join(lines)
    for chunk in joined.split(";"):
        stmt = chunk.strip()
        if stmt:
            yield stmt


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        raise NotImplementedError(
            "Baseline 0001 поддерживает только SQLite. Для PostgreSQL нужен "
            "отдельный диалект-специфичный baseline (см. docs/postgres-migration.md, Этап 6B)."
        )
    sql_text = SCHEMA_SQL.read_text(encoding="utf-8")
    for stmt in _statements(sql_text):
        if stmt.upper().startswith("PRAGMA"):
            continue
        bind.exec_driver_sql(stmt)


def downgrade() -> None:
    raise NotImplementedError("Откат baseline-миграции не поддерживается.")
