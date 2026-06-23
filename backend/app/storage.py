"""Слой доступа к данным поверх SQLite.

Раньше здесь были in-memory dict'ы; теперь все операции выполняются через
SQL-запросы к базе (см. app/db.py и app/schema.sql). Функции принимают/возвращают
те же dataclass-модели (app/models.py), поэтому роутеры почти не изменились.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import UUID, uuid4

from . import db, dialect
from .models import Chat, Message, Notification, UserInDB, UserRole, Attachment, StagedUpload

# Порядок удаления: сначала зависимые таблицы, затем родительские.
_ALL_TABLES = [
    "audit_logs",
    "role_upgrade_requests",
    "chat_roles",
    "chat_invites",
    "user_blocks",
    "message_reactions",
    "email_verification_tokens",
    "password_reset_tokens",
    "user_sessions",
    "attachments",
    "staged_uploads",
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
    keys = r.keys()
    return UserInDB(
        nickname=r["nickname"],
        role=UserRole(r["role"]),
        hashed_password=r["password_hash"],
        email=(r["email"] or "") if "email" in keys else "",
        first_name=(r["first_name"] or "") if "first_name" in keys else "",
        last_name=(r["last_name"] or "") if "last_name" in keys else "",
        email_verified=bool(r["email_verified"]) if "email_verified" in keys else False,
        avatar_url=r["avatar_url"] if "avatar_url" in keys and r["avatar_url"] else None,
        id=UUID(r["id"]),
        created_at=_parse(r["created_at"]),
        is_active=bool(r["is_active"]),
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


def _row_to_message(r: sqlite3.Row, is_read: bool = False, attachments: list | None = None) -> Message:
    return Message(
        chat_id=UUID(r["chat_id"]),
        author_id=UUID(r["author_id"]) if r["author_id"] else None,
        text=r["body"] or "",
        id=UUID(r["id"]),
        sent_at=_parse(r["created_at"]),
        is_read=is_read,
        edited_at=_parse(r["edited_at"]),
        attachments=attachments or [],
    )


def _row_to_attachment(r: sqlite3.Row) -> Attachment:
    return Attachment(
        message_id=UUID(r["message_id"]),
        kind=r["kind"],
        storage_key=r["storage_key"],
        file_name=r["file_name"],
        mime_type=r["mime_type"],
        size_bytes=r["size_bytes"],
        checksum=r["checksum"],
        id=UUID(r["id"]),
        created_at=_parse(r["created_at"]),
    )


def _row_to_staged_upload(r: sqlite3.Row) -> StagedUpload:
    return StagedUpload(
        uploader_id=UUID(r["uploader_id"]),
        storage_key=r["storage_key"],
        kind=r["kind"],
        file_name=r["file_name"],
        mime_type=r["mime_type"],
        size_bytes=int(r["size_bytes"]),
        checksum=r["checksum"],
        expires_at=_parse(r["expires_at"]),
        id=UUID(r["id"]),
        created_at=_parse(r["created_at"]),
        consumed_at=_parse(r["consumed_at"]),
        message_id=UUID(r["message_id"]) if r["message_id"] else None,
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
        if dialect.is_sqlite():
            conn.execute("PRAGMA foreign_keys=OFF;")
            for table in _ALL_TABLES:
                conn.execute(f"DELETE FROM {table};")
            conn.execute("PRAGMA foreign_keys=ON;")
        else:
            for table in _ALL_TABLES:
                conn.execute(f"DELETE FROM {table};")
        conn.commit()


# --------------------------- users ---------------------------


def create_user(user: UserInDB) -> None:
    ts = _fmt(user.created_at or _now())
    db.execute_script(
        [
            (
                "INSERT INTO users "
                "(id, nickname, password_hash, role, first_name, last_name, email, "
                "email_verified, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    str(user.id),
                    user.nickname,
                    user.hashed_password,
                    user.role.value,
                    user.first_name,
                    user.last_name,
                    user.email,
                    1 if user.email_verified else 0,
                    ts,
                    ts,
                ),
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


def update_password(user_id: UUID, password_hash: str) -> None:
    db.execute(
        "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
        (password_hash, _now_str(), str(user_id)),
    )


def set_role(user_id: UUID, role: UserRole) -> None:
    """Назначение роли пользователю (админское действие / сидинг)."""
    db.execute(
        "UPDATE users SET role=?, updated_at=? WHERE id=?",
        (role.value, _now_str(), str(user_id)),
    )


def set_active(user_id: UUID, is_active: bool) -> None:
    """Блокировка / разблокировка пользователя (админское действие)."""
    db.execute(
        "UPDATE users SET is_active=?, updated_at=? WHERE id=?",
        (1 if is_active else 0, _now_str(), str(user_id)),
    )


def list_users(limit: int = 100, offset: int = 0) -> list[UserInDB]:
    rows = db.query_all(
        "SELECT * FROM users WHERE deleted_at IS NULL "
        "ORDER BY created_at LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return [_row_to_user(r) for r in rows]


def count_active_admins() -> int:
    """Число активных админов — для защиты от блокировки последнего admin."""
    r = db.query_one(
        "SELECT COUNT(*) AS c FROM users "
        "WHERE role='admin' AND is_active=1 AND deleted_at IS NULL"
    )
    return int(r["c"]) if r else 0


def get_user_by_email(email: str) -> UserInDB | None:
    r = db.query_one(
        "SELECT * FROM users WHERE email=? AND deleted_at IS NULL", (email,)
    )
    return _row_to_user(r) if r else None


def mark_email_verified(user_id: UUID) -> None:
    db.execute(
        "UPDATE users SET email_verified=1, updated_at=? WHERE id=?",
        (_now_str(), str(user_id)),
    )


# --------------------------- email verification tokens ---------------------------


def create_email_verification_token(
    user_id: UUID, email: str, token_hash: str, expires_at: datetime
) -> None:
    """Создаёт новый токен подтверждения, инвалидируя прежние активные токены."""
    now = _now_str()
    db.execute_script(
        [
            (
                "UPDATE email_verification_tokens SET consumed_at=? "
                "WHERE user_id=? AND consumed_at IS NULL",
                (now, str(user_id)),
            ),
            (
                "INSERT INTO email_verification_tokens "
                "(id, user_id, token_hash, email, created_at, expires_at) "
                "VALUES (?,?,?,?,?,?)",
                (str(uuid4()), str(user_id), token_hash, email, now, _fmt(expires_at)),
            ),
        ]
    )


def get_active_email_token(token_hash: str) -> sqlite3.Row | None:
    """Возвращает неиспользованный и неистёкший токен по его хэшу."""
    return db.query_one(
        "SELECT * FROM email_verification_tokens "
        "WHERE token_hash=? AND consumed_at IS NULL AND expires_at > ?",
        (token_hash, _now_str()),
    )


def consume_email_token(token_id: str | UUID) -> None:
    db.execute(
        "UPDATE email_verification_tokens SET consumed_at=? WHERE id=?",
        (_now_str(), str(token_id)),
    )


def last_email_token_created_at(user_id: UUID) -> datetime | None:
    r = db.query_one(
        "SELECT created_at FROM email_verification_tokens "
        "WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (str(user_id),),
    )
    return _parse(r["created_at"]) if r else None


def count_email_tokens_since(user_id: UUID, since: datetime) -> int:
    r = db.query_one(
        "SELECT COUNT(*) AS c FROM email_verification_tokens "
        "WHERE user_id=? AND created_at >= ?",
        (str(user_id), _fmt(since)),
    )
    return int(r["c"]) if r else 0


# --------------------------- password reset tokens ---------------------------


def create_password_reset_token(
    user_id: UUID, token_hash: str, expires_at: datetime
) -> None:
    """Создаёт новый токен сброса пароля, инвалидируя прежние активные."""
    now = _now_str()
    db.execute_script(
        [
            (
                "UPDATE password_reset_tokens SET consumed_at=? "
                "WHERE user_id=? AND consumed_at IS NULL",
                (now, str(user_id)),
            ),
            (
                "INSERT INTO password_reset_tokens "
                "(id, user_id, token_hash, created_at, expires_at) "
                "VALUES (?,?,?,?,?)",
                (str(uuid4()), str(user_id), token_hash, now, _fmt(expires_at)),
            ),
        ]
    )


def get_active_password_reset_token(token_hash: str) -> sqlite3.Row | None:
    return db.query_one(
        "SELECT * FROM password_reset_tokens "
        "WHERE token_hash=? AND consumed_at IS NULL AND expires_at > ?",
        (token_hash, _now_str()),
    )


def consume_password_reset_token(token_id: str | UUID) -> None:
    db.execute(
        "UPDATE password_reset_tokens SET consumed_at=? WHERE id=?",
        (_now_str(), str(token_id)),
    )


def last_password_reset_token_created_at(user_id: UUID) -> datetime | None:
    r = db.query_one(
        "SELECT created_at FROM password_reset_tokens "
        "WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
        (str(user_id),),
    )
    return _parse(r["created_at"]) if r else None


def count_password_reset_tokens_since(user_id: UUID, since: datetime) -> int:
    r = db.query_one(
        "SELECT COUNT(*) AS c FROM password_reset_tokens "
        "WHERE user_id=? AND created_at >= ?",
        (str(user_id), _fmt(since)),
    )
    return int(r["c"]) if r else 0


# --------------------------- user sessions (refresh tokens) ---------------------------


def create_session(
    user_id: UUID,
    refresh_token_hash: str,
    expires_at: datetime,
    user_agent: str | None = None,
    ip: str | None = None,
) -> UUID:
    session_id = uuid4()
    now = _now_str()
    db.execute(
        "INSERT INTO user_sessions "
        "(id, user_id, refresh_token_hash, user_agent, ip, created_at, last_seen_at, expires_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            str(session_id),
            str(user_id),
            refresh_token_hash,
            user_agent,
            ip,
            now,
            now,
            _fmt(expires_at),
        ),
    )
    return session_id


def get_active_session_by_refresh(refresh_token_hash: str) -> sqlite3.Row | None:
    return db.query_one(
        "SELECT * FROM user_sessions "
        "WHERE refresh_token_hash=? AND revoked_at IS NULL AND expires_at > ?",
        (refresh_token_hash, _now_str()),
    )


def get_session(session_id: str | UUID) -> sqlite3.Row | None:
    return db.query_one(
        "SELECT * FROM user_sessions WHERE id=?", (str(session_id),)
    )


def rotate_session(
    session_id: str | UUID, new_refresh_token_hash: str, new_expires_at: datetime
) -> None:
    now = _now_str()
    db.execute(
        "UPDATE user_sessions "
        "SET refresh_token_hash=?, last_seen_at=?, expires_at=? "
        "WHERE id=?",
        (new_refresh_token_hash, now, _fmt(new_expires_at), str(session_id)),
    )


def revoke_session(session_id: str | UUID) -> int:
    return db.execute(
        "UPDATE user_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL",
        (_now_str(), str(session_id)),
    )


def revoke_session_by_refresh(refresh_token_hash: str) -> int:
    return db.execute(
        "UPDATE user_sessions SET revoked_at=? "
        "WHERE refresh_token_hash=? AND revoked_at IS NULL",
        (_now_str(), refresh_token_hash),
    )


def revoke_all_sessions(user_id: UUID) -> int:
    return db.execute(
        "UPDATE user_sessions SET revoked_at=? "
        "WHERE user_id=? AND revoked_at IS NULL",
        (_now_str(), str(user_id)),
    )


def list_active_sessions(user_id: UUID) -> list[sqlite3.Row]:
    return db.query_all(
        "SELECT * FROM user_sessions "
        "WHERE user_id=? AND revoked_at IS NULL AND expires_at > ? "
        "ORDER BY last_seen_at DESC",
        (str(user_id), _now_str()),
    )


# --------------------------- audit logs ---------------------------


def create_audit_log(
    action: str,
    entity_type: str,
    actor_id: UUID | None = None,
    entity_id: str | UUID | None = None,
    data: dict | None = None,
) -> None:
    db.execute(
        "INSERT INTO audit_logs (id, actor_id, action, entity_type, entity_id, data, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            str(uuid4()),
            str(actor_id) if actor_id else None,
            action,
            entity_type,
            str(entity_id) if entity_id else None,
            json.dumps(data or {}, ensure_ascii=False),
            _now_str(),
        ),
    )


def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: UUID | None = None,
) -> list[sqlite3.Row]:
    clauses: list[str] = []
    params: list = []
    if action:
        clauses.append("action = ?")
        params.append(action)
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)
    if actor_id:
        clauses.append("actor_id = ?")
        params.append(str(actor_id))
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.extend([limit, offset])
    return db.query_all(
        f"SELECT * FROM audit_logs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params),
    )


# --------------------------- role upgrade requests ---------------------------


def create_role_upgrade_request(
    user_id: UUID, requested_role: str, reason: str | None
) -> sqlite3.Row:
    request_id = uuid4()
    db.execute(
        "INSERT INTO role_upgrade_requests "
        "(id, user_id, requested_role, status, reason, created_at) "
        "VALUES (?,?,?,'pending',?,?)",
        (str(request_id), str(user_id), requested_role, reason, _now_str()),
    )
    row = get_role_upgrade_request(request_id)
    assert row is not None
    return row


def get_role_upgrade_request(request_id: str | UUID) -> sqlite3.Row | None:
    return db.query_one(
        "SELECT * FROM role_upgrade_requests WHERE id=?", (str(request_id),)
    )


def get_pending_request_for_user(user_id: UUID) -> sqlite3.Row | None:
    return db.query_one(
        "SELECT * FROM role_upgrade_requests "
        "WHERE user_id=? AND status='pending'",
        (str(user_id),),
    )


def list_role_upgrade_requests(
    status: str | None = None, limit: int = 100, offset: int = 0
) -> list[sqlite3.Row]:
    where = " WHERE status = ?" if status else ""
    params: list = [status] if status else []
    params.extend([limit, offset])
    return db.query_all(
        f"SELECT * FROM role_upgrade_requests{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params),
    )


def list_role_upgrade_requests_for_user(user_id: UUID) -> list[sqlite3.Row]:
    return db.query_all(
        "SELECT * FROM role_upgrade_requests WHERE user_id=? ORDER BY created_at DESC",
        (str(user_id),),
    )


def review_role_upgrade_request(
    request_id: str | UUID, status: str, reviewed_by: UUID, note: str | None
) -> None:
    db.execute(
        "UPDATE role_upgrade_requests "
        "SET status=?, reviewed_by=?, review_note=?, reviewed_at=? "
        "WHERE id=?",
        (status, str(reviewed_by), note, _now_str(), str(request_id)),
    )


def touch_last_seen(user_id: UUID) -> None:
    db.execute(
        "UPDATE users SET last_seen_at=?, updated_at=? WHERE id=? AND deleted_at IS NULL",
        (_now_str(), _now_str(), str(user_id)),
    )


def search_users(query: str, exclude_id: UUID, limit: int) -> list[UserInDB]:
    like = f"%{query.strip()}%"
    like_op = dialect.like_operator()
    rows = db.query_all(
        "SELECT u.* FROM users u "
        "JOIN user_privacy_settings p ON p.user_id = u.id "
        f"WHERE u.deleted_at IS NULL AND u.id <> ? AND p.searchable = 1 AND u.nickname {like_op} ? "
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


def create_message(msg: Message, *, body: str | None = None) -> None:
    text = body if body is not None else (msg.text or None)
    db.execute(
        "INSERT INTO messages (id, chat_id, author_id, type, body, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (str(msg.id), str(msg.chat_id), str(msg.author_id), "text", text, _fmt(msg.sent_at)),
    )


def list_messages(chat_id: UUID, limit: int, offset: int) -> list[Message]:
    rows = db.query_all(
        "SELECT * FROM messages WHERE chat_id=? AND deleted_at IS NULL "
        "ORDER BY created_at ASC, rowid ASC LIMIT ? OFFSET ?",
        (str(chat_id), limit, offset),
    )
    watermarks = _watermarks(chat_id)
    msg_ids = [r["id"] for r in rows]
    att_map = list_attachments_for_messages([UUID(mid) for mid in msg_ids])
    return [
        _row_to_message(
            r,
            _is_read(r["author_id"], r["created_at"], watermarks),
            att_map.get(UUID(r["id"]), []),
        )
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


# --------------------------- avatars ---------------------------


def get_avatar_key(user_id: UUID) -> str | None:
    r = db.query_one("SELECT avatar_url FROM users WHERE id=?", (str(user_id),))
    return r["avatar_url"] if r and r["avatar_url"] else None


def set_avatar_key(user_id: UUID, key: str | None) -> None:
    db.execute(
        "UPDATE users SET avatar_url=?, updated_at=? WHERE id=?",
        (key, _now_str(), str(user_id)),
    )


def get_avatar_visibility(user_id: UUID) -> str:
    r = db.query_one(
        "SELECT avatar_visibility FROM user_privacy_settings WHERE user_id=?",
        (str(user_id),),
    )
    return r["avatar_visibility"] if r else "public"


def can_view_avatar(target_user_id: UUID, viewer_id: UUID) -> bool:
    if target_user_id == viewer_id:
        return True
    visibility = get_avatar_visibility(target_user_id)
    if visibility == "private":
        return False
    if visibility == "public":
        return True
    # participants: общий активный чат
    r = db.query_one(
        "SELECT 1 FROM chat_participants p1 "
        "JOIN chat_participants p2 ON p1.chat_id = p2.chat_id AND p2.user_id = ? "
        "WHERE p1.user_id = ? AND p1.left_at IS NULL AND p2.left_at IS NULL LIMIT 1",
        (str(viewer_id), str(target_user_id)),
    )
    return r is not None


# --------------------------- attachments ---------------------------


def create_attachment(att: Attachment) -> None:
    db.execute(
        "INSERT INTO attachments "
        "(id, message_id, kind, storage_key, file_name, mime_type, size_bytes, checksum, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            str(att.id),
            str(att.message_id),
            att.kind,
            att.storage_key,
            att.file_name,
            att.mime_type,
            att.size_bytes,
            att.checksum,
            _fmt(att.created_at or _now()),
        ),
    )


def get_attachment(attachment_id: UUID) -> Attachment | None:
    r = db.query_one("SELECT * FROM attachments WHERE id=?", (str(attachment_id),))
    return _row_to_attachment(r) if r else None


def list_attachments_for_messages(message_ids: list[UUID]) -> dict[UUID, list[Attachment]]:
    if not message_ids:
        return {}
    placeholders = ",".join("?" * len(message_ids))
    rows = db.query_all(
        f"SELECT * FROM attachments WHERE message_id IN ({placeholders}) ORDER BY created_at",
        tuple(str(mid) for mid in message_ids),
    )
    result: dict[UUID, list[Attachment]] = {}
    for r in rows:
        mid = UUID(r["message_id"])
        result.setdefault(mid, []).append(_row_to_attachment(r))
    return result


# --------------------------- staged uploads ---------------------------


def create_staged_upload(staged: StagedUpload) -> None:
    db.execute(
        "INSERT INTO staged_uploads "
        "(id, uploader_id, storage_key, kind, file_name, mime_type, size_bytes, checksum, "
        "created_at, expires_at, consumed_at, message_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            str(staged.id),
            str(staged.uploader_id),
            staged.storage_key,
            staged.kind,
            staged.file_name,
            staged.mime_type,
            staged.size_bytes,
            staged.checksum,
            _fmt(staged.created_at or _now()),
            _fmt(staged.expires_at),
            _fmt(staged.consumed_at) if staged.consumed_at else None,
            str(staged.message_id) if staged.message_id else None,
        ),
    )


def get_staged_upload(upload_id: UUID) -> StagedUpload | None:
    r = db.query_one("SELECT * FROM staged_uploads WHERE id=?", (str(upload_id),))
    return _row_to_staged_upload(r) if r else None


def mark_staged_upload_consumed(upload_id: UUID, message_id: UUID | None = None) -> None:
    db.execute(
        "UPDATE staged_uploads SET consumed_at=?, message_id=? WHERE id=?",
        (_now_str(), str(message_id) if message_id else None, str(upload_id)),
    )
