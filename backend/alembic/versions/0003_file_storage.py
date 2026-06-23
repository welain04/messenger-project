"""staged_uploads + relaxed messages.body CHECK + attachment indexes

Revision ID: 0003_file_storage
Revises: 0002_password_reset_tokens
"""

from __future__ import annotations

from alembic import op

revision = "0003_file_storage"
down_revision = "0002_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        raise NotImplementedError(
            "0003_file_storage поддерживает только SQLite (см. docs/postgres-migration.md)."
        )

    bind.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS staged_uploads (
            id          TEXT PRIMARY KEY,
            uploader_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            storage_key TEXT NOT NULL,
            kind        TEXT NOT NULL CHECK (kind IN ('image','video','audio','file')),
            file_name   TEXT,
            mime_type   TEXT,
            size_bytes  INTEGER NOT NULL,
            checksum    TEXT,
            created_at  TEXT NOT NULL,
            expires_at  TEXT NOT NULL,
            consumed_at TEXT,
            message_id  TEXT REFERENCES messages(id) ON DELETE SET NULL
        )
        """
    )
    bind.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_staged_uploads_storage_key "
        "ON staged_uploads (storage_key)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_staged_uploads_uploader "
        "ON staged_uploads (uploader_id, consumed_at)"
    )
    bind.exec_driver_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_attachments_storage_key "
        "ON attachments (storage_key)"
    )

    # SQLite: пересоздаём messages с ослабленным CHECK (body может быть NULL/пустым).
    bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
    bind.exec_driver_sql(
        """
        CREATE TABLE messages_new (
            id                        TEXT PRIMARY KEY,
            chat_id                   TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            author_id                 TEXT REFERENCES users(id) ON DELETE SET NULL,
            type                      TEXT NOT NULL DEFAULT 'text' CHECK (type IN ('text','system')),
            body                      TEXT,
            reply_to_message_id       TEXT REFERENCES messages(id) ON DELETE SET NULL,
            forwarded_from_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
            forwarded_from_chat_id    TEXT REFERENCES chats(id)    ON DELETE SET NULL,
            original_author_id        TEXT REFERENCES users(id)    ON DELETE SET NULL,
            created_at                TEXT NOT NULL,
            edited_at                 TEXT,
            deleted_at                TEXT,
            CHECK (
                type <> 'text' OR body IS NULL OR length(body) BETWEEN 0 AND 2000
            )
        )
        """
    )
    bind.exec_driver_sql(
        """
        INSERT INTO messages_new SELECT * FROM messages
        """
    )
    bind.exec_driver_sql("DROP TABLE messages")
    bind.exec_driver_sql("ALTER TABLE messages_new RENAME TO messages")
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_messages_chat_created ON messages (chat_id, created_at)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_messages_author ON messages (author_id)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_messages_reply_to ON messages (reply_to_message_id)"
    )
    bind.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_messages_forwarded_from ON messages (forwarded_from_message_id)"
    )
    bind.exec_driver_sql("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    bind = op.get_bind()
    bind.exec_driver_sql("DROP INDEX IF EXISTS uq_attachments_storage_key")
    bind.exec_driver_sql("DROP INDEX IF EXISTS ix_staged_uploads_uploader")
    bind.exec_driver_sql("DROP INDEX IF EXISTS uq_staged_uploads_storage_key")
    bind.exec_driver_sql("DROP TABLE IF EXISTS staged_uploads")
