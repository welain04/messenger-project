"""Лёгкие миграции SQLite для уже существующих messenger.db (ADD COLUMN)."""

from __future__ import annotations

import sqlite3

# Порядок важен. CREATE TABLE IF NOT EXISTS не добавляет колонки в старые таблицы.
_MIGRATION_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE users ADD COLUMN last_seen_at TEXT",
    "ALTER TABLE user_privacy_settings ADD COLUMN display_name_visibility TEXT NOT NULL DEFAULT 'public'",
    "ALTER TABLE notifications ADD COLUMN actor_id TEXT REFERENCES users(id) ON DELETE SET NULL",
    "ALTER TABLE notifications ADD COLUMN chat_id TEXT REFERENCES chats(id) ON DELETE SET NULL",
    "ALTER TABLE notifications ADD COLUMN message_id TEXT REFERENCES messages(id) ON DELETE SET NULL",
    "CREATE INDEX IF NOT EXISTS ix_notifications_chat ON notifications (chat_id)",
)


def run_migrations(conn: sqlite3.Connection) -> None:
    for sql in _MIGRATION_STATEMENTS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
