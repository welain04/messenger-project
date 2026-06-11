-- SQLite-схема Online School Messenger.
-- Адаптация db-design.md под SQLite:
--   * UUID         -> TEXT (строковый UUID)
--   * timestamptz  -> TEXT (ISO-8601, UTC)
--   * ENUM         -> TEXT + CHECK (...)
--   * citext       -> TEXT COLLATE NOCASE
--   * jsonb        -> TEXT (JSON)
--   * boolean      -> INTEGER (0/1)
-- Идентификаторы и временные метки генерируются на стороне Python.

PRAGMA foreign_keys = ON;

-- ============ USERS ============
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    nickname      TEXT NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student','curator','admin')),
    display_name  TEXT,
    avatar_url    TEXT,
    email         TEXT COLLATE NOCASE,
    bio           TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    last_seen_at  TEXT,
    deleted_at    TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_nickname ON users (nickname);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email    ON users (email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_users_role            ON users (role);

-- ============ USER PRIVACY SETTINGS (1:1) ============
CREATE TABLE IF NOT EXISTS user_privacy_settings (
    user_id              TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email_visibility     TEXT NOT NULL DEFAULT 'private'      CHECK (email_visibility     IN ('public','participants','private')),
    bio_visibility       TEXT NOT NULL DEFAULT 'public'       CHECK (bio_visibility       IN ('public','participants','private')),
    last_seen_visibility TEXT NOT NULL DEFAULT 'participants' CHECK (last_seen_visibility IN ('public','participants','private')),
    avatar_visibility       TEXT NOT NULL DEFAULT 'public'       CHECK (avatar_visibility       IN ('public','participants','private')),
    display_name_visibility TEXT NOT NULL DEFAULT 'public'       CHECK (display_name_visibility IN ('public','participants','private')),
    searchable              INTEGER NOT NULL DEFAULT 1 CHECK (searchable IN (0,1)),
    updated_at           TEXT NOT NULL
);

-- ============ USER SETTINGS (1:1) ============
CREATE TABLE IF NOT EXISTS user_settings (
    user_id               TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    locale                TEXT NOT NULL DEFAULT 'ru',
    theme                 TEXT NOT NULL DEFAULT 'system',
    notifications_enabled INTEGER NOT NULL DEFAULT 1 CHECK (notifications_enabled IN (0,1)),
    updated_at            TEXT NOT NULL
);

-- ============ CHATS ============
CREATE TABLE IF NOT EXISTS chats (
    id           TEXT PRIMARY KEY,
    type         TEXT NOT NULL CHECK (type IN ('personal','group')),
    title        TEXT,
    created_by   TEXT REFERENCES users(id) ON DELETE SET NULL,
    personal_key TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    deleted_at   TEXT,
    CHECK (
        (type = 'group'    AND title IS NOT NULL) OR
        (type = 'personal' AND title IS NULL)
    ),
    CHECK (
        (type = 'personal' AND personal_key IS NOT NULL) OR
        (type = 'group'    AND personal_key IS NULL)
    )
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_chats_personal_key ON chats (personal_key) WHERE personal_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_chats_created_by ON chats (created_by);

-- ============ MESSAGES ============
-- Создаётся до chat_participants: на messages ссылается last_read_message_id.
CREATE TABLE IF NOT EXISTS messages (
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
        type <> 'text' OR (body IS NOT NULL AND length(body) BETWEEN 1 AND 2000)
    )
);
CREATE INDEX IF NOT EXISTS ix_messages_chat_created   ON messages (chat_id, created_at);
CREATE INDEX IF NOT EXISTS ix_messages_author         ON messages (author_id);
CREATE INDEX IF NOT EXISTS ix_messages_reply_to       ON messages (reply_to_message_id);
CREATE INDEX IF NOT EXISTS ix_messages_forwarded_from ON messages (forwarded_from_message_id);

-- ============ CHAT PARTICIPANTS (M:N + read watermark) ============
CREATE TABLE IF NOT EXISTS chat_participants (
    id                   TEXT PRIMARY KEY,
    chat_id              TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id              TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role                 TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','admin','member')),
    joined_at            TEXT NOT NULL,
    last_read_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    last_read_at         TEXT,
    muted                INTEGER NOT NULL DEFAULT 0 CHECK (muted IN (0,1)),
    left_at              TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_participant ON chat_participants (chat_id, user_id) WHERE left_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_participants_user ON chat_participants (user_id) WHERE left_at IS NULL;
CREATE INDEX IF NOT EXISTS ix_participants_chat ON chat_participants (chat_id) WHERE left_at IS NULL;

-- ============ MESSAGE READS (read receipts) ============
CREATE TABLE IF NOT EXISTS message_reads (
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    read_at    TEXT NOT NULL,
    PRIMARY KEY (message_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_message_reads_user ON message_reads (user_id, message_id);

-- ============ NOTIFICATIONS ============
-- Адаптация: добавлена текстовая колонка `message` (человекочитаемый текст),
-- т.к. приложение оперирует строкой сообщения; payload оставлен для будущего.
CREATE TABLE IF NOT EXISTS notifications (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       TEXT NOT NULL DEFAULT 'system'
                CHECK (type IN ('new_message','added_to_chat','removed_from_chat','mention','system')),
    message    TEXT NOT NULL,
    actor_id   TEXT REFERENCES users(id) ON DELETE SET NULL,
    chat_id    TEXT REFERENCES chats(id) ON DELETE SET NULL,
    message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
    payload    TEXT NOT NULL DEFAULT '{}',
    is_read    INTEGER NOT NULL DEFAULT 0 CHECK (is_read IN (0,1)),
    created_at TEXT NOT NULL,
    read_at    TEXT
);
CREATE INDEX IF NOT EXISTS ix_notifications_user_unread ON notifications (user_id, is_read, created_at);

-- ============ ATTACHMENTS ============
CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,
    message_id  TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL CHECK (kind IN ('image','video','audio','file')),
    storage_key TEXT NOT NULL,
    file_name   TEXT,
    mime_type   TEXT,
    size_bytes  INTEGER CHECK (size_bytes IS NULL OR size_bytes >= 0),
    width       INTEGER,
    height      INTEGER,
    checksum    TEXT,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_attachments_message ON attachments (message_id);

-- ============ USER SESSIONS ============
CREATE TABLE IF NOT EXISTS user_sessions (
    id                 TEXT PRIMARY KEY,
    user_id            TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash TEXT NOT NULL,
    user_agent         TEXT,
    ip                 TEXT,
    created_at         TEXT NOT NULL,
    last_seen_at       TEXT NOT NULL,
    expires_at         TEXT NOT NULL,
    revoked_at         TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_sessions_token ON user_sessions (refresh_token_hash);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON user_sessions (user_id) WHERE revoked_at IS NULL;

-- ============ MESSAGE REACTIONS (future) ============
CREATE TABLE IF NOT EXISTS message_reactions (
    message_id TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    emoji      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (message_id, user_id, emoji)
);
CREATE INDEX IF NOT EXISTS ix_reactions_message ON message_reactions (message_id);

-- ============ USER BLOCKS (future) ============
CREATE TABLE IF NOT EXISTS user_blocks (
    blocker_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (blocker_id, blocked_id),
    CHECK (blocker_id <> blocked_id)
);
CREATE INDEX IF NOT EXISTS ix_blocks_blocked ON user_blocks (blocked_id);

-- ============ CHAT INVITES (future) ============
CREATE TABLE IF NOT EXISTS chat_invites (
    id         TEXT PRIMARY KEY,
    chat_id    TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    token      TEXT NOT NULL,
    max_uses   INTEGER,
    uses       INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_invite_token ON chat_invites (token);
CREATE INDEX IF NOT EXISTS ix_invites_chat ON chat_invites (chat_id);

-- ============ CHAT ROLES (future) ============
CREATE TABLE IF NOT EXISTS chat_roles (
    id          TEXT PRIMARY KEY,
    chat_id     TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    permissions TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL,
    UNIQUE (chat_id, name)
);

-- ============ AUDIT LOGS (future) ============
CREATE TABLE IF NOT EXISTS audit_logs (
    id          TEXT PRIMARY KEY,
    actor_id    TEXT REFERENCES users(id) ON DELETE SET NULL,
    action      TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id   TEXT,
    data        TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_actor  ON audit_logs (actor_id, created_at);
