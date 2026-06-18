"""password_reset_tokens table

Revision ID: 0002_password_reset_tokens
Revises: 0001_initial
"""

from __future__ import annotations

from alembic import op

revision = "0002_password_reset_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        raise NotImplementedError(
            "0002_password_reset_tokens поддерживает только SQLite (см. docs/postgres-migration.md)."
        )
    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash  TEXT NOT NULL,
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            consumed_at TEXT
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_prt_token_hash "
        "ON password_reset_tokens (token_hash)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_prt_user "
        "ON password_reset_tokens (user_id, consumed_at)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP INDEX IF EXISTS ix_prt_user")
    bind.exec_driver_sql("DROP INDEX IF EXISTS uq_prt_token_hash")
    bind.exec_driver_sql("DROP TABLE IF EXISTS password_reset_tokens")
