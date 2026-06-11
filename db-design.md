# Проектирование реляционной БД — Online School Messenger (PostgreSQL)

> Проектирование схемы данных, обоснования и SQL DDL. Без кода FastAPI/SQLAlchemy/Alembic/ORM/миграций.

---

## 1. Сущности и их назначение

### Ядро (MVP)
| Сущность | Назначение |
|---|---|
| `users` | Аккаунты. Аутентификационные данные (hash пароля), роль, базовый публичный профиль. |
| `user_privacy_settings` | Настройки приватности: что из профиля видно другим (публичное vs приватное). Вынесено отдельно, т.к. это «1 к 1» с пользователем и часто расширяется. |
| `chats` | Чаты обоих типов (`personal` / `group`). Для группового — название и создатель. |
| `chat_participants` | Членство пользователей в чатах (M:N). Здесь же роль внутри чата и «водяной знак» прочтения (`last_read_*`) для подсчёта непрочитанного. |
| `messages` | Сообщения. Soft delete, редактирование, пересылка, ответы, системные сообщения. |
| `notifications` | Персональные уведомления (новое сообщение, добавление в чат и т.д.). |

### Рекомендуемые (ближайшее развитие)
| Сущность | Назначение |
|---|---|
| `attachments` | Метаданные вложений (файлы/изображения). Сами файлы — в объектном хранилище (S3/MinIO), в БД только ссылки и метаданные. |
| `message_reads` | Точные «прочтения» на уровне сообщения (read receipts: кто и когда прочитал конкретное сообщение). Дополняет водяной знак, не заменяет его. |
| `user_sessions` | Серверный учёт сессий/устройств: refresh-токены, отзыв доступа, «выйти на всех устройствах», подготовка к WebSocket-presence. |
| `user_settings` | Общие пользовательские настройки приложения (язык, тема, флаги уведомлений) — в отличие от `user_privacy_settings`, которые управляют видимостью данных. |

### На будущее (заложить, но не обязательно реализовывать сейчас)
| Сущность | Назначение |
|---|---|
| `message_reactions` | Реакции (эмодзи) на сообщения. |
| `user_blocks` | Блокировки пользователей (анти-спам, безопасность). |
| `chat_invites` | Приглашения/ссылки-приглашения в групповые чаты. |
| `chat_roles` | Расширяемая ролевая модель внутри чата (если перерастём enum-роль в гибкую систему прав). |
| `audit_logs` | Журнал значимых действий для безопасности и расследований. |

> **Решение по `chat_roles`:** на старте роль участника в чате храним enum-колонкой в `chat_participants` (`owner`/`admin`/`member`) — это покрывает «создатель/куратор управляет участниками». Отдельная таблица `chat_roles` нужна только когда понадобятся произвольные наборы прав (capabilities). Включена в раздел «на будущее».

---

## 2. ER-диаграмма (текстовый вид)

```
                         ┌───────────────────────┐
                         │        users          │
                         │  (PK id)              │
                         └───────────────────────┘
        1:1 │                 1:N │   1:N │            1:N │
            ▼                     ▼       ▼                ▼
 ┌────────────────────┐  ┌──────────────┐ ┌───────────────┐ ┌───────────────┐
 │user_privacy_settings│ │ user_settings│ │ user_sessions │ │ notifications │
 └────────────────────┘  └──────────────┘ └───────────────┘ └───────────────┘

   users ──< chat_participants >── chats           (M:N через chat_participants)
   users  1:N  chats               (created_by)
   chat_participants N:1 messages  (last_read_message_id — водяной знак)
   chats  1:N  messages
   users  1:N  messages            (author_id)
   messages ──< message_reads >── users            (M:N: кто прочитал сообщение)
   messages 1:N attachments
   messages ──< message_reactions >── users
   messages self-FK: forwarded_from_message_id, reply_to_message_id
   chats   1:N  chat_invites
   notifications N:1 users (actor_id), chats, messages  (опц. FK)
   users ──< user_blocks >── users                 (self M:N: blocker/blocked)
   chats 1:N chat_roles (опц.)  ;  audit_logs.actor_id → users
```

Связи «звезда вокруг users» + «звезда вокруг messages» + связующая `chat_participants` между `users` и `chats`.

---

## 3. Описание связей

- **users 1:1 user_privacy_settings** — у каждого пользователя ровно один набор настроек приватности (`user_id` PK+FK).
- **users 1:1 user_settings** — аналогично, общие настройки.
- **users 1:N user_sessions / notifications** — много сессий и уведомлений на пользователя.
- **users M:N chats** через **chat_participants** — пользователь в нескольких чатах, в чате несколько пользователей.
- **users 1:N chats** — создатель группового чата (`chats.created_by`).
- **chat_participants N:1 messages** — водяной знак прочтения (`last_read_message_id`).
- **chats 1:N messages** — сообщения принадлежат чату (`messages.chat_id`).
- **users 1:N messages** — автор сообщения (`messages.author_id`).
- **messages self-reference**:
  - `reply_to_message_id` → ответы/треды;
  - `forwarded_from_message_id` → исходное сообщение при пересылке (+ `forwarded_from_chat_id`, `original_author_id` как снимок).
- **messages M:N users** через **message_reads** — кто прочитал конкретное сообщение (read receipts).
- **messages 1:N attachments** — несколько вложений на сообщение.
- **messages M:N users** через **message_reactions** — реакции.
- **chats 1:N chat_invites** — приглашения в чат.
- **users M:N users** через **user_blocks** (blocker_id / blocked_id).
- **notifications** — опциональные FK: `actor_id` → users, `chat_id` → chats, `message_id` → messages (плюс `payload` jsonb).
- **audit_logs.actor_id → users** — кто совершил действие.

> **Поле `is_read` в API сообщений** не хранится в `messages` — вычисляется при чтении ленты на основе водяного знака участников.

Стратегия удаления:
- Сообщения, чаты, пользователи — **soft delete** (`deleted_at`/`is_active`); в приложении удаление чата — `UPDATE chats SET deleted_at`.
- FK заданы с разумными `ON DELETE` (CASCADE для зависимых записей чата, SET NULL для исторических ссылок типа `forwarded_from`/`original_author`, RESTRICT там, где потеря недопустима) — на случай реального hard-delete и для целостности.

---

## 4. Детальное описание таблиц

Ниже — поля, типы, ключи, ограничения и индексы. Точные определения — в DDL (раздел 9).

### ENUM-типы
- `user_role`: `student`, `curator`, `admin`(future)
- `chat_type`: `personal`, `group`
- `chat_member_role`: `owner`, `admin`, `member`
- `message_type`: `text`, `system`
- `notification_type`: `new_message`, `added_to_chat`, `removed_from_chat`, `mention`, `system`
- `visibility_level`: `public`, `participants`, `private`
- `attachment_kind`: `image`, `video`, `audio`, `file`

### `users`
| Поле | Тип | Примечания |
|---|---|---|
| id | uuid PK | `gen_random_uuid()` |
| nickname | citext | **UNIQUE**, NOT NULL, CHECK длина 3..30 и `~ '^[A-Za-z0-9_]+$'` |
| password_hash | text | NOT NULL (только hash) |
| role | user_role | NOT NULL, default `student` |
| display_name | text | публичное имя (опц.) |
| avatar_url | text | опц. |
| email | citext | приватное, UNIQUE (nullable) |
| bio | text | приватное/публичное по настройке |
| is_active | boolean | default true (soft-блокировка/деактивация) |
| created_at | timestamptz | default now() |
| updated_at | timestamptz | default now() |
| last_seen_at | timestamptz NULL | «был в сети» (обновляется при активности API) |
| deleted_at | timestamptz NULL | soft delete |

Индексы: UNIQUE(nickname), UNIQUE(email) where email not null, индекс по `role`, индекс для поиска `nickname gin_trgm_ops` (поиск по подстроке).

### `user_privacy_settings` (1:1)
| Поле | Тип | Примечания |
|---|---|---|
| user_id | uuid PK, FK→users(id) ON DELETE CASCADE | |
| email_visibility | visibility_level | default `private` |
| bio_visibility | visibility_level | default `public` |
| last_seen_visibility | visibility_level | default `participants` |
| avatar_visibility | visibility_level | default `public` |
| display_name_visibility | visibility_level | default `public` |
| searchable | boolean | default true (попадает ли в поиск) |
| updated_at | timestamptz | |

### `user_settings` (1:1, рекомендуемая)
| Поле | Тип |
|---|---|
| user_id | uuid PK, FK→users ON DELETE CASCADE |
| locale | text default 'ru' |
| theme | text default 'system' |
| notifications_enabled | boolean default true |
| updated_at | timestamptz |

### `chats`
| Поле | Тип | Примечания |
|---|---|---|
| id | uuid PK | |
| type | chat_type | NOT NULL |
| title | text | NULL для personal, NOT NULL для group (CHECK) |
| created_by | uuid FK→users(id) ON DELETE SET NULL | |
| personal_key | text | для personal: детерминированный ключ пары (минId:максId), **UNIQUE**; NULL для group — предотвращает дубли личных чатов |
| created_at | timestamptz | |
| updated_at | timestamptz | |
| deleted_at | timestamptz NULL | |

- CHECK: `(type='group' AND title IS NOT NULL) OR (type='personal' AND title IS NULL)`.
- CHECK: `(type='personal' AND personal_key IS NOT NULL) OR (type='group' AND personal_key IS NULL)`.
- Индексы: UNIQUE(personal_key), индекс по `created_by`.

### `chat_participants` (M:N + состояние прочтения)
| Поле | Тип | Примечания |
|---|---|---|
| id | uuid PK | |
| chat_id | uuid FK→chats ON DELETE CASCADE | |
| user_id | uuid FK→users ON DELETE CASCADE | |
| role | chat_member_role | default `member` |
| joined_at | timestamptz | момент входа |
| last_read_message_id | uuid FK→messages ON DELETE SET NULL | водяной знак прочтения |
| last_read_at | timestamptz NULL | время последнего прочтения |
| left_at | timestamptz NULL | soft-выход / удаление из чата |
| muted | boolean default false | |

- **UNIQUE partial**: `(chat_id, user_id) WHERE left_at IS NULL` — активное членство уникально, но допускает повторное добавление в истории.
- Индексы: по `user_id` (список чатов пользователя), по `chat_id`.

> Новый участник группового чата «получает доступ ко всей истории» автоматически — доступ определяется фактом активного участия. `joined_at` оставлен на случай будущей политики ограничения видимости ранних сообщений.

### `messages`
| Поле | Тип | Примечания |
|---|---|---|
| id | uuid PK | |
| chat_id | uuid FK→chats ON DELETE CASCADE | NOT NULL |
| author_id | uuid FK→users ON DELETE SET NULL | NULL допустим (автор удалён) |
| type | message_type | default `text` |
| body | text | CHECK длина ≤ 2000 для text |
| reply_to_message_id | uuid FK→messages ON DELETE SET NULL | треды/ответы |
| forwarded_from_message_id | uuid FK→messages ON DELETE SET NULL | пересылка |
| forwarded_from_chat_id | uuid FK→chats ON DELETE SET NULL | пересылка |
| original_author_id | uuid FK→users ON DELETE SET NULL | снимок автора оригинала |
| created_at | timestamptz | default now() |
| edited_at | timestamptz NULL | дата изменения |
| deleted_at | timestamptz NULL | **soft delete** |

- CHECK для `type='text'`: `body` 1..2000 символов.
- **`is_read` не является колонкой** — только вычисляемое поле API.

Индексы: **`(chat_id, created_at DESC)`** — пагинация ленты; индекс по `author_id`; **partial** `(chat_id, created_at) WHERE deleted_at IS NULL`; опц. `body gin_trgm_ops` для поиска по тексту.

### `message_reads` (рекомендуемая — read receipts)
| Поле | Тип |
|---|---|
| message_id | uuid FK→messages ON DELETE CASCADE |
| user_id | uuid FK→users ON DELETE CASCADE |
| read_at | timestamptz default now() |

- **PK составной (message_id, user_id)**.
- Индекс по `(user_id, message_id)`.

### `notifications`
| Поле | Тип |
|---|---|
| id | uuid PK |
| user_id | uuid FK→users ON DELETE CASCADE |
| type | notification_type |
| message | text NOT NULL | человекочитаемый текст для UI |
| actor_id | uuid FK→users ON DELETE SET NULL | кто инициировал событие (опц.) |
| chat_id | uuid FK→chats ON DELETE SET NULL | связанный чат (опц.) |
| message_id | uuid FK→messages ON DELETE SET NULL | связанное сообщение (опц.) |
| payload | jsonb | расширенный контекст, deep links |
| is_read | boolean default false |
| created_at | timestamptz default now() |
| read_at | timestamptz NULL |

Индексы: **`(user_id, is_read, created_at DESC)`**; опц. `(chat_id)` для фильтра по чату.

### `attachments` (рекомендуемая)
| Поле | Тип |
|---|---|
| id | uuid PK |
| message_id | uuid FK→messages ON DELETE CASCADE |
| kind | attachment_kind |
| storage_key | text NOT NULL (ключ в объектном хранилище) |
| file_name | text |
| mime_type | text |
| size_bytes | bigint CHECK ≥ 0 |
| width / height | int NULL |
| checksum | text NULL |
| created_at | timestamptz |

Индекс по `message_id`.

### `user_sessions` (рекомендуемая)
| Поле | Тип |
|---|---|
| id | uuid PK |
| user_id | uuid FK→users ON DELETE CASCADE |
| refresh_token_hash | text (только hash) |
| user_agent / ip | text/inet |
| created_at, last_seen_at, expires_at | timestamptz |
| revoked_at | timestamptz NULL |

Индекс по `(user_id)`, UNIQUE(refresh_token_hash).

### Будущие таблицы (кратко)
- **`message_reactions`** — PK `(message_id, user_id, emoji)`; FK на messages/users; `created_at`.
- **`user_blocks`** — PK `(blocker_id, blocked_id)`; оба FK→users; CHECK `blocker_id <> blocked_id`; `created_at`.
- **`chat_invites`** — `id`, `chat_id` FK, `created_by` FK, `token` UNIQUE, `expires_at`, `max_uses`, `uses`, `created_at`.
- **`chat_roles`** — `id`, `chat_id` FK, `name`, `permissions jsonb`, UNIQUE(chat_id, name).
- **`audit_logs`** — `id`, `actor_id` FK→users SET NULL, `action`, `entity_type`, `entity_id`, `data jsonb`, `created_at`; индексы по `(entity_type, entity_id)` и `(actor_id, created_at)`.

---

## 5. Логика хранения непрочитанных сообщений

**Гибридный подход** — это и есть «наиболее эффективная структура»:

1. **Основной механизм — водяной знак (watermark) в `chat_participants`:**
   - `last_read_message_id` + `last_read_at` на каждого участника в каждом чате.
   - **Количество непрочитанных** = число живых сообщений в чате с `created_at` позже `last_read_*` и `author_id <> user_id`.
   - Стоимость хранения **O(участники чата)**, а не O(сообщения × участники). Обновление прочтения — один UPDATE. Масштабируется на миллионы сообщений.
   - Запрос счётчика быстрый благодаря индексу `(chat_id, created_at)`.

2. **Дополнительный механизм — `message_reads` (read receipts):**
   - Нужен только если требуется «кто именно и когда прочитал конкретное сообщение».
   - Дорогая по объёму таблица, поэтому **не используется для счётчиков**, только для точечных receipt-ов.

**Почему не только `message_reads`:** наивная отметка каждого сообщения порождает взрывной рост строк и тяжёлые записи. Watermark решает 95% задач дёшево; `message_reads` подключается опционально.

Глобальный бейдж «сколько всего непрочитано» — агрегируем счётчики по `chat_participants` пользователя (можно кэшировать в Redis при переходе на WebSocket).

---

## 6. Логика хранения пересланных сообщений

Пересылка = **создание нового сообщения** в целевом чате со ссылками на оригинал:

- `forwarded_from_message_id` → исходное сообщение (`ON DELETE SET NULL`).
- `forwarded_from_chat_id` → исходный чат.
- `original_author_id` → **снимок** автора оригинала.
- `body` копируется (денормализованный снимок текста) — пересланное сообщение остаётся читаемым, даже если оригинал отредактирован/удалён или нет доступа к исходному чату.

Преимущества:
- Атрибуция («переслано от X») сохраняется через `original_author_id` + снимок текста.
- Нет утечки доступа: получатель не получает прав на исходный чат — только копию.
- Цепочки пересылок поддерживаются (идём по `forwarded_from_message_id`); `original_author_id` лучше проставлять от самого первого источника.
- `reply_to_message_id` — отдельная самоссылка для ответов/тредов, не путать с пересылкой.

---

## 7. Логика хранения настроек приватности

- Отдельная таблица **`user_privacy_settings` (1:1 к users)**:
  - Разделение публичных/приватных данных — **на уровне видимости полей**, а не дублированием профиля. Каждое чувствительное поле имеет свой `visibility_level` (`public` / `participants` / `private`).
  - Пример: `email_visibility=private`, `last_seen_visibility=participants`, `bio_visibility=public`.
  - `searchable` управляет попаданием пользователя в поиск.
- **Применение на чтении:** backend формирует ответ, фильтруя поля по их visibility и отношениям (сам пользователь / участник общего чата / посторонний).
- **Почему отдельная таблица:** настройки приватности часто расширяются независимо от профиля; строки `users` остаются компактными.
- `user_settings` отделены от privacy: приватность = «что видят другие», settings = «как работает приложение для меня».

---

## 8. Структура хранения вложений

Принцип: **файлы — в объектном хранилище (S3/MinIO), в БД — только метаданные.**

- Таблица **`attachments`**, связь `messages 1:N attachments`.
- Метаданные: `kind`, `storage_key`, `file_name`, `mime_type`, `size_bytes`, `width/height`, `checksum`.
- Никаких `bytea` для больших файлов — это экономит размер БД, ускоряет бэкапы, позволяет отдавать файлы через CDN/pre-signed URL.
- Добавление картинок/файлов/видео не требует изменения схемы сообщений — только записи в `attachments`. Превью/варианты размеров — на будущее в `attachment_variants`.
- Целостность: `ON DELETE CASCADE` от message; при soft-delete вложения остаются, физическая очистка — фоновым воркером по `deleted_at`.

---

## 9. Полный SQL DDL (PostgreSQL)

```sql
-- ============ Расширения ============
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- регистронезависимые nickname/email
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- поиск по подстроке

-- ============ ENUM-типы ============
CREATE TYPE user_role         AS ENUM ('student', 'curator', 'admin');
CREATE TYPE chat_type         AS ENUM ('personal', 'group');
CREATE TYPE chat_member_role  AS ENUM ('owner', 'admin', 'member');
CREATE TYPE message_type      AS ENUM ('text', 'system');
CREATE TYPE notification_type AS ENUM ('new_message','added_to_chat','removed_from_chat','mention','system');
CREATE TYPE visibility_level  AS ENUM ('public', 'participants', 'private');
CREATE TYPE attachment_kind   AS ENUM ('image', 'video', 'audio', 'file');

-- ============ USERS ============
CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nickname      citext NOT NULL,
    password_hash text   NOT NULL,
    role          user_role NOT NULL DEFAULT 'student',
    display_name  text,
    avatar_url    text,
    email         citext,
    bio           text,
    is_active     boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at  timestamptz,
    deleted_at    timestamptz,
    CONSTRAINT users_nickname_format CHECK (nickname ~ '^[A-Za-z0-9_]{3,30}$')
);
CREATE UNIQUE INDEX uq_users_nickname ON users (nickname);
CREATE UNIQUE INDEX uq_users_email    ON users (email) WHERE email IS NOT NULL;
CREATE INDEX ix_users_role            ON users (role);
CREATE INDEX ix_users_nickname_trgm   ON users USING gin (nickname gin_trgm_ops);

-- ============ USER PRIVACY SETTINGS (1:1) ============
CREATE TABLE user_privacy_settings (
    user_id              uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email_visibility     visibility_level NOT NULL DEFAULT 'private',
    bio_visibility       visibility_level NOT NULL DEFAULT 'public',
    last_seen_visibility visibility_level NOT NULL DEFAULT 'participants',
    avatar_visibility       visibility_level NOT NULL DEFAULT 'public',
    display_name_visibility visibility_level NOT NULL DEFAULT 'public',
    searchable              boolean NOT NULL DEFAULT true,
    updated_at              timestamptz NOT NULL DEFAULT now()
);

-- ============ USER SETTINGS (1:1) ============
CREATE TABLE user_settings (
    user_id               uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    locale                text NOT NULL DEFAULT 'ru',
    theme                 text NOT NULL DEFAULT 'system',
    notifications_enabled boolean NOT NULL DEFAULT true,
    updated_at            timestamptz NOT NULL DEFAULT now()
);

-- ============ CHATS ============
CREATE TABLE chats (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type         chat_type NOT NULL,
    title        text,
    created_by   uuid REFERENCES users(id) ON DELETE SET NULL,
    personal_key text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now(),
    deleted_at   timestamptz,
    CONSTRAINT chats_title_rule CHECK (
        (type = 'group'    AND title IS NOT NULL AND char_length(title) BETWEEN 1 AND 100) OR
        (type = 'personal' AND title IS NULL)
    ),
    CONSTRAINT chats_personal_key_rule CHECK (
        (type = 'personal' AND personal_key IS NOT NULL) OR
        (type = 'group'    AND personal_key IS NULL)
    )
);
CREATE UNIQUE INDEX uq_chats_personal_key ON chats (personal_key) WHERE personal_key IS NOT NULL;
CREATE INDEX ix_chats_created_by ON chats (created_by);

-- ============ MESSAGES ============
-- (создаётся до chat_participants, т.к. chat_participants ссылается на messages)
CREATE TABLE messages (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id                   uuid NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    author_id                 uuid REFERENCES users(id) ON DELETE SET NULL,
    type                      message_type NOT NULL DEFAULT 'text',
    body                      text,
    reply_to_message_id       uuid REFERENCES messages(id) ON DELETE SET NULL,
    forwarded_from_message_id uuid REFERENCES messages(id) ON DELETE SET NULL,
    forwarded_from_chat_id    uuid REFERENCES chats(id)    ON DELETE SET NULL,
    original_author_id        uuid REFERENCES users(id)    ON DELETE SET NULL,
    created_at                timestamptz NOT NULL DEFAULT now(),
    edited_at                 timestamptz,
    deleted_at                timestamptz,
    CONSTRAINT messages_text_len CHECK (
        type <> 'text' OR (body IS NOT NULL AND char_length(body) BETWEEN 1 AND 2000)
    )
);
CREATE INDEX ix_messages_chat_created      ON messages (chat_id, created_at DESC);
CREATE INDEX ix_messages_chat_live         ON messages (chat_id, created_at) WHERE deleted_at IS NULL;
CREATE INDEX ix_messages_author            ON messages (author_id);
CREATE INDEX ix_messages_reply_to          ON messages (reply_to_message_id);
CREATE INDEX ix_messages_forwarded_from    ON messages (forwarded_from_message_id);
CREATE INDEX ix_messages_body_trgm         ON messages USING gin (body gin_trgm_ops);

-- ============ CHAT PARTICIPANTS (M:N + read watermark) ============
CREATE TABLE chat_participants (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id              uuid NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    user_id              uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role                 chat_member_role NOT NULL DEFAULT 'member',
    joined_at            timestamptz NOT NULL DEFAULT now(),
    last_read_message_id uuid REFERENCES messages(id) ON DELETE SET NULL,
    last_read_at         timestamptz,
    muted                boolean NOT NULL DEFAULT false,
    left_at              timestamptz
);
CREATE UNIQUE INDEX uq_active_participant
    ON chat_participants (chat_id, user_id) WHERE left_at IS NULL;
CREATE INDEX ix_participants_user ON chat_participants (user_id) WHERE left_at IS NULL;
CREATE INDEX ix_participants_chat ON chat_participants (chat_id) WHERE left_at IS NULL;

-- ============ MESSAGE READS (read receipts) ============
CREATE TABLE message_reads (
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    uuid NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    read_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (message_id, user_id)
);
CREATE INDEX ix_message_reads_user ON message_reads (user_id, message_id);

-- ============ NOTIFICATIONS ============
CREATE TABLE notifications (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type       notification_type NOT NULL,
    message    text NOT NULL,
    actor_id   uuid REFERENCES users(id) ON DELETE SET NULL,
    chat_id    uuid REFERENCES chats(id) ON DELETE SET NULL,
    message_id uuid REFERENCES messages(id) ON DELETE SET NULL,
    payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
    is_read    boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    read_at    timestamptz
);
CREATE INDEX ix_notifications_user_unread ON notifications (user_id, is_read, created_at DESC);
CREATE INDEX ix_notifications_chat ON notifications (chat_id);

-- ============ ATTACHMENTS ============
CREATE TABLE attachments (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id  uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    kind        attachment_kind NOT NULL,
    storage_key text NOT NULL,
    file_name   text,
    mime_type   text,
    size_bytes  bigint CHECK (size_bytes IS NULL OR size_bytes >= 0),
    width       int,
    height      int,
    checksum    text,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_attachments_message ON attachments (message_id);

-- ============ USER SESSIONS ============
CREATE TABLE user_sessions (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash text NOT NULL,
    user_agent         text,
    ip                 inet,
    created_at         timestamptz NOT NULL DEFAULT now(),
    last_seen_at       timestamptz NOT NULL DEFAULT now(),
    expires_at         timestamptz NOT NULL,
    revoked_at         timestamptz
);
CREATE UNIQUE INDEX uq_sessions_token ON user_sessions (refresh_token_hash);
CREATE INDEX ix_sessions_user ON user_sessions (user_id) WHERE revoked_at IS NULL;

-- ============ MESSAGE REACTIONS (future) ============
CREATE TABLE message_reactions (
    message_id uuid NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    user_id    uuid NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    emoji      text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (message_id, user_id, emoji)
);
CREATE INDEX ix_reactions_message ON message_reactions (message_id);

-- ============ USER BLOCKS (future) ============
CREATE TABLE user_blocks (
    blocker_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    blocked_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (blocker_id, blocked_id),
    CONSTRAINT no_self_block CHECK (blocker_id <> blocked_id)
);
CREATE INDEX ix_blocks_blocked ON user_blocks (blocked_id);

-- ============ CHAT INVITES (future) ============
CREATE TABLE chat_invites (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id    uuid NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    created_by uuid REFERENCES users(id) ON DELETE SET NULL,
    token      text NOT NULL,
    max_uses   int,
    uses       int NOT NULL DEFAULT 0,
    expires_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_invite_token ON chat_invites (token);
CREATE INDEX ix_invites_chat ON chat_invites (chat_id);

-- ============ CHAT ROLES (future, расширяемые права) ============
CREATE TABLE chat_roles (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id     uuid NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    name        text NOT NULL,
    permissions jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_chat_role UNIQUE (chat_id, name)
);

-- ============ AUDIT LOGS (future) ============
CREATE TABLE audit_logs (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id    uuid REFERENCES users(id) ON DELETE SET NULL,
    action      text NOT NULL,
    entity_type text NOT NULL,
    entity_id   uuid,
    data        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_audit_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX ix_audit_actor  ON audit_logs (actor_id, created_at DESC);
```

> Порядок создания: `messages` создаётся до `chat_participants`, т.к. `chat_participants.last_read_message_id` ссылается на `messages`, а `messages.chat_id` — на `chats`. Рекомендуется триггер `updated_at = now()` на таблицах с этим полем.

---

## 10. Группировка таблиц по этапам

**Обязательные для MVP**
- `users`
- `user_privacy_settings`
- `chats`
- `chat_participants` (с `last_read_message_id`/`last_read_at` — непрочитанное закрывается здесь без отдельной таблицы)
- `messages` (soft delete + пересылка + ответы)
- `notifications`

**Рекомендуемые для ближайшего развития**
- `attachments` (вложения/изображения/файлы)
- `message_reads` (точные read receipts в группах)
- `user_sessions` (refresh-токены, отзыв доступа, подготовка к WebSocket)
- `user_settings` (язык/тема/нотификации)

**Заложить на будущее**
- `message_reactions`
- `user_blocks`
- `chat_invites`
- `chat_roles` (гибкие права, когда enum-роли станет мало)
- `audit_logs`

---

## Соответствие требованиям безопасности и масштабирования
- **Пароли** — только `password_hash`; refresh-токены — только `refresh_token_hash`.
- **Приватность/ПДн** — разделение публичного и приватного через `visibility_level` + `user_privacy_settings`, фильтрация на чтении.
- **Роли** — enum `user_role` (student/curator/admin) глобально и `chat_member_role` внутри чата; путь расширения — `chat_roles.permissions jsonb` без ломки схемы.
- **Целостность** — все связи на UUID-FK с продуманными `ON DELETE` (CASCADE/SET NULL/исторические снимки), CHECK-ограничения на бизнес-правила.
- **Масштаб** — watermark вместо построчных прочтений; вложения вне БД; индексы под основные паттерны; `jsonb payload` в уведомлениях/аудите для гибких событий и интеграции с очередями/WebSocket; UUID-ключи дружелюбны к шардированию.
- **Партиционирование (на вырост)** — `messages` и `notifications` — кандидаты на партиционирование по времени (`created_at`) или по `chat_id`.
