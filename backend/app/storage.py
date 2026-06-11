"""Слой доступа к данным поверх SQLite.

Раньше здесь были in-memory dict'ы; теперь все операции выполняются через
SQL-запросы к базе (см. app/db.py и app/schema.sql). Функции принимают/возвращают
те же dataclass-модели (app/models.py), поэтому роутеры почти не изменились.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4

from . import db
from .models import Chat, Message, Notification, UserInDB, UserRole

# Порядок удаления: сначала зависимые таблицы, затем родительские.
_ALL_TABLES = [
    "audit_logs",
    "chat_roles",
    "chat_invites",
    "user_blocks",
    "message_reactions",
    "user_sessions",
    "attachments",
    "notifications",
    "message_reads",
    "chat_participants",
    "messages",
    "user_settings",
    "user_privacy_settings",
    "chats",
    "users",
]


class StorageError(Exception):
    """Нарушение целостности данных (например, дубликат личного чата)."""


# --------------------------- утилиты времени ---------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    """Единый формат хранения времени: UTC, ISO-8601, микросекунды.

    Фиксированная длина строки нужна для корректного лексикографического
    сравнения временных меток в SQL (unread_count / is_read).
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _now_str() -> str:
    return _fmt(_now())


# --------------------------- row -> model ---------------------------


def _row_to_user(r: sqlite3.Row) -> UserInDB:
    return UserInDB(
        nickname=r["nickname"],
        role=UserRole(r["role"]),
        hashed_password=r["password_hash"],
        id=UUID(r["id"]),
        created_at=_parse(r["created_at"]),
    )


def _row_to_chat(r: sqlite3.Row, participant_ids: list[UUID]) -> Chat:
    return Chat(
        type=r["type"],
        participant_ids=participant_ids,
        created_by=UUID(r["created_by"]) if r["created_by"] else None,
        title=r["title"],
        id=UUID(r["id"]),
        created_at=_parse(r["created_at"]),
    )


def _row_to_message(r: sqlite3.Row, is_read: bool = False) -> Message:
    return Message(
        chat_id=UUID(r["chat_id"]),
        author_id=UUID(r["author_id"]) if r["author_id"] else None,
        text=r["body"],
        id=UUID(r["id"]),
        sent_at=_parse(r["created_at"]),
        is_read=is_read,
        edited_at=_parse(r["edited_at"]),
    )


def _row_to_notification(r: sqlite3.Row) -> Notification:
    return Notification(
        user_id=UUID(r["user_id"]),
        message=r["message"],
        id=UUID(r["id"]),
        is_read=bool(r["is_read"]),
        created_at=_parse(r["created_at"]),
    )


# --------------------------- обслуживание ---------------------------


def reset_storage() -> None:
    """Полная очистка всех таблиц (для тестов и сидинга)."""
    conn = db.get_connection()
    with db.lock:
        conn.execute("PRAGMA foreign_keys=OFF;")
        for table in _ALL_TABLES:
            conn.execute(f"DELETE FROM {table};")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.commit()


# --------------------------- users ---------------------------


def create_user(user: UserInDB) -> None:
    ts = _fmt(user.created_at or _now())
    db.execute_script(
        [
            (
                "INSERT INTO users (id, nickname, password_hash, role, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?)",
                (str(user.id), user.nickname, user.hashed_password, user.role.value, ts, ts),
            ),
            (
                "INSERT INTO user_privacy_settings (user_id, updated_at) VALUES (?,?)",
                (str(user.id), ts),
            ),
            (
                "INSERT INTO user_settings (user_id, updated_at) VALUES (?,?)",
                (str(user.id), ts),
            ),
        ]
    )


def get_user(user_id: UUID) -> UserInDB | None:
    r = db.query_one(
        "SELECT * FROM users WHERE id=? AND deleted_at IS NULL", (str(user_id),)
    )
    return _row_to_user(r) if r else None


def get_user_by_nickname(nickname: str) -> UserInDB | None:
    r = db.query_one(
        "SELECT * FROM users WHERE nickname=? AND deleted_at IS NULL", (nickname,)
    )
    return _row_to_user(r) if r else None


def user_exists(user_id: UUID) -> bool:
    return (
        db.query_one(
            "SELECT 1 FROM users WHERE id=? AND deleted_at IS NULL", (str(user_id),)
        )
        is not None
    )


def update_nickname(user_id: UUID, new_nickname: str) -> None:
    db.execute(
        "UPDATE users SET nickname=?, updated_at=? WHERE id=?",
        (new_nickname, _now_str(), str(user_id)),
    )


def touch_last_seen(user_id: UUID) -> None:
    db.execute(
        "UPDATE users SET last_seen_at=?, updated_at=? WHERE id=? AND deleted_at IS NULL",
        (_now_str(), _now_str(), str(user_id)),
    )


def search_users(query: str, exclude_id: UUID, limit: int) -> list[UserInDB]:
    like = f"%{query.strip()}%"
    rows = db.query_all(
        "SELECT u.* FROM users u "
        "JOIN user_privacy_settings p ON p.user_id = u.id "
        "WHERE u.deleted_at IS NULL AND u.id <> ? AND p.searchable = 1 AND u.nickname LIKE ? "
        "ORDER BY u.nickname COLLATE NOCASE LIMIT ?",
        (str(exclude_id), like, limit),
    )
    return [_row_to_user(r) for r in rows]


# --------------------------- chats ---------------------------


def _personal_key(participant_ids: list[UUID]) -> str:
    return ":".join(sorted(str(p) for p in participant_ids))


def find_personal_chat(participant_ids: list[UUID]) -> Chat | None:
    key = _personal_key(participant_ids)
    r = db.query_one(
        "SELECT * FROM chats WHERE personal_key=? AND deleted_at IS NULL", (key,)
    )
    if not r:
        return None
    return _row_to_chat(r, _participant_ids(r["id"]))


def create_chat(chat: Chat) -> None:
    ts = _fmt(chat.created_at or _now())
    personal_key = _personal_key(chat.participant_ids) if chat.type == "personal" else None
    statements: list[tuple[str, tuple]] = [
        (
            "INSERT INTO chats (id, type, title, created_by, personal_key, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(chat.id), chat.type, chat.title, str(chat.created_by), personal_key, ts, ts),
        )
    ]
    for pid in chat.participant_ids:
        role = "owner" if pid == chat.created_by else "member"
        statements.append(
            (
                "INSERT INTO chat_participants (id, chat_id, user_id, role, joined_at) "
                "VALUES (?,?,?,?,?)",
                (str(uuid4()), str(chat.id), str(pid), role, ts),
            )
        )
    try:
        db.execute_script(statements)
    except sqlite3.IntegrityError as exc:
        raise StorageError(str(exc)) from exc


def _participant_ids(chat_id: str | UUID) -> list[UUID]:
    rows = db.query_all(
        "SELECT user_id FROM chat_participants WHERE chat_id=? AND left_at IS NULL "
        "ORDER BY joined_at",
        (str(chat_id),),
    )
    return [UUID(r["user_id"]) for r in rows]


def get_chat(chat_id: UUID) -> Chat | None:
    r = db.query_one(
        "SELECT * FROM chats WHERE id=? AND deleted_at IS NULL", (str(chat_id),)
    )
    if not r:
        return None
    return _row_to_chat(r, _participant_ids(chat_id))


def list_chats_for_user(user_id: UUID) -> list[Chat]:
    rows = db.query_all(
        "SELECT c.* FROM chats c "
        "JOIN chat_participants p ON p.chat_id = c.id "
        "WHERE p.user_id=? AND p.left_at IS NULL AND c.deleted_at IS NULL",
        (str(user_id),),
    )
    return [_row_to_chat(r, _participant_ids(r["id"])) for r in rows]


def is_participant(chat_id: UUID, user_id: UUID) -> bool:
    return (
        db.query_one(
            "SELECT 1 FROM chat_participants WHERE chat_id=? AND user_id=? AND left_at IS NULL",
            (str(chat_id), str(user_id)),
        )
        is not None
    )


def add_participant(chat_id: UUID, user_id: UUID, role: str = "member") -> None:
    now = _now_str()
    reactivated = db.execute(
        "UPDATE chat_participants SET left_at=NULL, role=?, joined_at=? "
        "WHERE chat_id=? AND user_id=? AND left_at IS NOT NULL",
        (role, now, str(chat_id), str(user_id)),
    )
    if reactivated == 0:
        db.execute(
            "INSERT INTO chat_participants (id, chat_id, user_id, role, joined_at) "
            "VALUES (?,?,?,?,?)",
            (str(uuid4()), str(chat_id), str(user_id), role, now),
        )


def remove_participant(chat_id: UUID, user_id: UUID) -> None:
    db.execute(
        "UPDATE chat_participants SET left_at=? WHERE chat_id=? AND user_id=? AND left_at IS NULL",
        (_now_str(), str(chat_id), str(user_id)),
    )


def delete_chat(chat_id: UUID) -> None:
    now = _now_str()
    db.execute(
        "UPDATE chats SET deleted_at=?, updated_at=? WHERE id=? AND deleted_at IS NULL",
        (now, now, str(chat_id)),
    )


# --------------------------- messages ---------------------------


def _watermarks(chat_id: UUID) -> dict[str, str | None]:
    rows = db.query_all(
        "SELECT user_id, last_read_at FROM chat_participants "
        "WHERE chat_id=? AND left_at IS NULL",
        (str(chat_id),),
    )
    return {r["user_id"]: r["last_read_at"] for r in rows}


def _is_read(author_id: str | None, created_at: str, watermarks: dict[str, str | None]) -> bool:
    """Сообщение считается прочитанным, если его прочитал хоть кто-то, кроме автора."""
    for uid, last_read in watermarks.items():
        if uid == author_id:
            continue
        if last_read is not None and last_read >= created_at:
            return True
    return False


def create_message(msg: Message) -> None:
    db.execute(
        "INSERT INTO messages (id, chat_id, author_id, type, body, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (str(msg.id), str(msg.chat_id), str(msg.author_id), "text", msg.text, _fmt(msg.sent_at)),
    )


def list_messages(chat_id: UUID, limit: int, offset: int) -> list[Message]:
    rows = db.query_all(
        "SELECT * FROM messages WHERE chat_id=? AND deleted_at IS NULL "
        "ORDER BY created_at ASC, rowid ASC LIMIT ? OFFSET ?",
        (str(chat_id), limit, offset),
    )
    watermarks = _watermarks(chat_id)
    return [
        _row_to_message(r, _is_read(r["author_id"], r["created_at"], watermarks))
        for r in rows
    ]


def get_message(message_id: UUID) -> Message | None:
    r = db.query_one(
        "SELECT * FROM messages WHERE id=? AND deleted_at IS NULL", (str(message_id),)
    )
    if not r:
        return None
    watermarks = _watermarks(UUID(r["chat_id"]))
    return _row_to_message(r, _is_read(r["author_id"], r["created_at"], watermarks))


def update_message(message_id: UUID, text: str) -> None:
    db.execute(
        "UPDATE messages SET body=?, edited_at=? WHERE id=?",
        (text, _now_str(), str(message_id)),
    )


def soft_delete_message(message_id: UUID) -> None:
    db.execute(
        "UPDATE messages SET deleted_at=? WHERE id=?", (_now_str(), str(message_id))
    )


def last_message(chat_id: UUID) -> Message | None:
    r = db.query_one(
        "SELECT * FROM messages WHERE chat_id=? AND deleted_at IS NULL "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (str(chat_id),),
    )
    return _row_to_message(r) if r else None


def unread_count(chat_id: UUID, user_id: UUID) -> int:
    r = db.query_one(
        "SELECT COUNT(*) AS cnt FROM messages m "
        "JOIN chat_participants p ON p.chat_id = m.chat_id AND p.user_id=? AND p.left_at IS NULL "
        "WHERE m.chat_id=? AND m.deleted_at IS NULL AND m.author_id <> ? "
        "AND (p.last_read_at IS NULL OR m.created_at > p.last_read_at)",
        (str(user_id), str(chat_id), str(user_id)),
    )
    return int(r["cnt"]) if r else 0


def mark_chat_read(chat_id: UUID, user_id: UUID) -> None:
    last = db.query_one(
        "SELECT id FROM messages WHERE chat_id=? AND deleted_at IS NULL "
        "ORDER BY created_at DESC, rowid DESC LIMIT 1",
        (str(chat_id),),
    )
    last_id = last["id"] if last else None
    db.execute(
        "UPDATE chat_participants SET last_read_at=?, last_read_message_id=? "
        "WHERE chat_id=? AND user_id=? AND left_at IS NULL",
        (_now_str(), last_id, str(chat_id), str(user_id)),
    )


# --------------------------- notifications ---------------------------


def create_notification(
    notification: Notification,
    ntype: str = "system",
    actor_id: UUID | None = None,
    chat_id: UUID | None = None,
    message_id: UUID | None = None,
) -> None:
    db.execute(
        "INSERT INTO notifications (id, user_id, type, message, actor_id, chat_id, message_id, "
        "is_read, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (
            str(notification.id),
            str(notification.user_id),
            ntype,
            notification.message,
            str(actor_id) if actor_id else None,
            str(chat_id) if chat_id else None,
            str(message_id) if message_id else None,
            1 if notification.is_read else 0,
            _fmt(notification.created_at or _now()),
        ),
    )


def list_notifications(user_id: UUID) -> list[Notification]:
    rows = db.query_all(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC",
        (str(user_id),),
    )
    return [_row_to_notification(r) for r in rows]


def get_notification(notification_id: UUID) -> Notification | None:
    r = db.query_one(
        "SELECT * FROM notifications WHERE id=?", (str(notification_id),)
    )
    return _row_to_notification(r) if r else None


def mark_notification_read(notification_id: UUID) -> None:
    db.execute(
        "UPDATE notifications SET is_read=1, read_at=? WHERE id=?",
        (_now_str(), str(notification_id)),
    )
