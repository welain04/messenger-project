# Online School Messenger — Backend

FastAPI-бэкенд мессенджера онлайн-школы. Хранение данных — в **SQLite** (файл
`messenger.db`, отдельный сервер БД не нужен). Схема применяется автоматически при
старте через **миграции Alembic** (`alembic upgrade head` в `init_db`); baseline-
миграция повторяет снимок `app/schema.sql` (адаптация `db-design.md` под SQLite).
Подготовка к PostgreSQL описана в `../docs/postgres-migration.md`. Авторизация —
JWT (HS256), пароли — bcrypt (passlib).

## Структура

```
backend/
  app/
    __init__.py
    config.py          # Settings (BaseSettings, читает .env), DATABASE_PATH
    main.py            # create_app(), init_db(), CORS, JWT-middleware, /api/v1
    middleware.py      # JWTUserMiddleware -> request.state.user
    deps.py            # get_current_user / get_current_user_or_none
    security.py        # хеш паролей, create/decode JWT
    db.py              # подключение к SQLite, init_db() (Alembic), database_url()
    dialect.py         # различия SQLite/PostgreSQL (диалект, LIKE/ILIKE, bool)
    alembic_runner.py  # программный запуск миграций Alembic
    migrations.py      # легаси ADD COLUMN-миграции для старых SQLite-баз
    schema.sql         # снимок DDL v1 (используется baseline-миграцией)
    storage.py         # слой доступа к данным (SQL-запросы), модели на входе/выходе
    models.py          # dataclass-модели UserInDB, Chat, Message, Notification
    schemas.py         # Pydantic-схемы запросов/ответов
    errors.py          # человекочитаемые ошибки валидации (без stack trace)
    rate_limit.py      # in-memory rate limiter (логин/регистрация и др.)
    permissions.py     # проверки прав доступа
    audit.py           # запись действий в audit_logs
    mailer.py          # отправка/логирование писем (verify / reset)
    deps_storage.py    # DI для StorageService / FileService
    services/
      files.py         # валидация (размер/тип по содержимому), оркестрация загрузок
      storage/         # провайдеры хранилища: local, yandex_s3
    routers/
      auth.py          # register/login/refresh/logout, verify-email, сброс пароля
      users.py         # профиль, аватар, сессии, заявки на повышение роли
      chats.py
      messages.py
      uploads.py       # staged-загрузки файлов
      files.py         # presigned-URL, отдача локальных файлов
      notifications.py
      admin.py         # управление пользователями/ролями, audit-logs
      test_support.py  # вспомогательные ручки для E2E (только при ENABLE_TEST_ENDPOINTS)
  static/              # test.html (ручная страница проверки API)
  scripts/
    export_openapi.py  # пишет openapi.json
    smoke_test.py      # сквозной TestClient-сценарий
    seed.py            # наполнение БД тестовыми данными
  alembic.ini          # конфигурация Alembic
  alembic/             # env.py + versions/ (миграции схемы)
  messenger.db         # файл SQLite (создаётся автоматически, в .gitignore)
  requirements.txt
  .env / .env.example
  openapi.json         # автогенерируемая схема
```

## Установка и запуск

```powershell
# 1. Перейти в папку
cd backend

# 2. Создать виртуальное окружение и поставить зависимости
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Скопировать переменные окружения
copy .env.example .env   # или используйте уже существующий .env

# 4. Запуск dev-сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

После старта:

- Swagger UI:   http://localhost:8000/docs
- ReDoc:        http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json
- Health:       http://localhost:8000/health

### Переменные окружения

Полный список с комментариями — в `.env.example`. Основные:

| Имя                          | Назначение                                 | По умолчанию                                                |
|------------------------------|--------------------------------------------|-------------------------------------------------------------|
| `APP_ENV`                    | `development` \| `production` \| `test`     | `development`                                               |
| `JWT_SECRET`                 | секрет подписи JWT                         | `change-me`                                                 |
| `JWT_ALGORITHM`              | алгоритм JWT                               | `HS256`                                                     |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| TTL access-токена в минутах                | `15`                                                        |
| `REFRESH_TOKEN_EXPIRE_DAYS`  | TTL refresh-токена в днях                  | `30`                                                        |
| `DATABASE_PATH`              | путь к файлу SQLite                        | `<backend>/messenger.db`                                    |
| `DATABASE_URL`              | URL для Alembic/Postgres (пусто → SQLite)  | _(пусто)_                                                   |
| `CORS_ORIGINS`               | разрешённые origin'ы через запятую (не `*`)| `http://localhost:5173,http://127.0.0.1:5173`               |
| `ENABLE_TEST_ENDPOINTS`      | тестовые ручки `/api/v1/_test/*` (E2E)     | `false`                                                     |
| `RATE_LIMIT_LOGIN_PER_MIN`   | лимит логинов в минуту на IP (`0` — выкл.) | `5`                                                         |
| `RATE_LIMIT_REGISTER_PER_MIN`| лимит регистраций в минуту на IP           | `5`                                                         |
| `RATE_LIMIT_FORGOT_PASSWORD_PER_MIN` | лимит запросов сброса пароля       | `3`                                                         |
| `TRUST_PROXY_HEADERS`        | учитывать `X-Forwarded-For` (за прокси)    | `false`                                                     |
| `TRUSTED_PROXY_COUNT`        | число доверенных прокси перед приложением  | `1`                                                         |
| `STORAGE_PROVIDER`           | `local` (dev) или `yandex` (S3)            | `local`                                                     |
| `AVATAR_MAX_BYTES`           | макс. размер аватара                       | `5242880` (5 МБ)                                            |
| `ATTACHMENT_MAX_BYTES`       | макс. размер вложения                      | `20971520` (20 МБ)                                          |
| `ALLOWED_AVATAR_MIMES`       | белый список MIME для аватаров             | `image/jpeg,image/png,image/webp`                          |
| `ALLOWED_ATTACHMENT_MIMES`   | белый список MIME для вложений             | _(см. `.env.example`)_                                      |
| `HOST` / `PORT`              | для собственных скриптов запуска           | `0.0.0.0` / `8000`                                          |

## Эндпоинты (`/api/v1`)

### Auth
- `POST /auth/register` — `{ nickname, password, role }` → `User`
- `POST /auth/login`    — `{ nickname, password }` → `{ access_token, token_type }`

### Users
- `GET   /users/me` → `User`
- `PATCH /users/me` `{ nickname }` → `User`

### Chats
- `POST   /chats` `{ type, title?, participant_ids }` → `Chat`
- `GET    /chats` → `Chat[]` (с `last_message`, `unread_count`)
- `GET    /chats/{chat_id}` → `Chat`
- `POST   /chats/{chat_id}/participants` `{ user_id }` → `Chat` (только group)
- `DELETE /chats/{chat_id}/participants/{user_id}` → 204
- `DELETE /chats/{chat_id}` → 204

### Messages
- `GET    /chats/{chat_id}/messages?limit=50&offset=0` → `Message[]`
- `POST   /chats/{chat_id}/messages` `{ text }` → `Message`
- `PATCH  /messages/{message_id}` `{ text }` → `Message`
- `DELETE /messages/{message_id}` → 204

### Notifications
- `GET   /notifications` → `Notification[]`
- `PATCH /notifications/{notification_id}/read` → `Notification`

## Правила доступа

- **User** — пользователь видит и меняет только себя.
- **Chat** — читать может только участник; добавлять/удалять участников и удалять
  чат может только `created_by` или пользователь с ролью `curator`.
- **Message** — отправлять/читать может участник чата; редактировать — только автор;
  удалять — автор или `curator`.
- **Notification** — доступна только своему владельцу.

## Валидация (Pydantic v2)

- `nickname`: 3..30 символов, `[A-Za-z0-9_]+`
- `password`: ≥ 6 символов
- `text` сообщения: 1..2000 символов
- `title` группового чата: 1..100 символов
- личный чат: ровно 2 участника, `title` запрещён
- групповой чат: ≥ 2 участника, `title` обязателен

## Безопасность

Реализованные меры:

- **SQL-инъекции** — все запросы в `storage.py`/`db.py` параметризованы (`?`-плейсхолдеры);
  f-строки в SQL содержат только внутренние константы, не пользовательский ввод.
- **CORS** (`app/main.py`) — белый список origin'ов (`CORS_ORIGINS`, не `*`),
  суженные методы (`GET/POST/PATCH/DELETE/OPTIONS`) и заголовки (`Authorization, Content-Type`).
- **Rate limit** (`app/rate_limit.py`) — на логин, регистрацию, refresh, подтверждение
  email и сброс пароля. Ключ — IP клиента; за прокси включается через `TRUST_PROXY_HEADERS`
  (с защитой от подделки `X-Forwarded-For`). Хранилище счётчиков — in-memory (для нескольких
  инстансов нужен Redis).
- **Ошибки наружу** — без stack trace; ошибки валидации переводятся в человекочитаемые
  русские сообщения (`app/errors.py`).
- **Загрузка файлов** (`app/services/files.py`) — проверка размера (413) и реального типа
  по сигнатуре содержимого через `filetype` (а не только по присланному `Content-Type`),
  сверка с белым списком MIME (415).
- **Секреты** — только в `.env` (в `.gitignore`); в коде секретов нет.
- **Защита конфигурации** (`app/config.py`) — при `APP_ENV=production` приложение
  не стартует со слабым `JWT_SECRET` или с включёнными тестовыми эндпоинтами.

### Чек-лист перед продакшеном

1. `APP_ENV=production` и стойкий `JWT_SECRET`
   (`python -c "import secrets; print(secrets.token_urlsafe(64))"`).
2. `CORS_ORIGINS` — реальный домен фронтенда (например `https://app.example.com`).
3. `ENABLE_TEST_ENDPOINTS=false`.
4. За nginx: `TRUST_PROXY_HEADERS=true`, корректный `TRUSTED_PROXY_COUNT`
   и `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`.
5. Боевые `STORAGE_PROVIDER`/S3-ключи и `SMTP_*` заданы и не закоммичены.
6. (При нескольких воркерах/инстансах) вынести rate limit в Redis.

## Полезные скрипты

```powershell
# Регенерировать openapi.json:
.\.venv\Scripts\python.exe scripts\export_openapi.py

# Прогон сквозного smoke-теста (отдельная БД .smoke_test.db, messenger.db не трогает):
.\.venv\Scripts\python.exe scripts\smoke_test.py

# Наполнить БД тестовыми данными (пользователи/чаты/сообщения):
.\.venv\Scripts\python.exe scripts\seed.py
```

После сидинга доступны пользователи `alice` (curator), `bob`, `carol`, `dave`
(student) с паролем `password123`, личный чат alice↔bob и групповой чат «Math 101».

### База данных

- Движок: SQLite, файл `messenger.db` в папке `backend` (путь можно переопределить
  переменной `DATABASE_PATH`).
- Таблицы применяются миграциями Alembic при старте приложения (`init_db` →
  `alembic upgrade head`). Изменения схемы оформляются новыми ревизиями Alembic
  (`cd backend && alembic revision -m "..."`), а не правкой `schema.sql`.
- **Пароль в `messenger.db` сам не меняется** — он пересоздаётся только если вы:
  - запускаете `scripts\seed.py` (полная очистка и новые тестовые пользователи);
  - удаляете файл `messenger.db` вручную;
  - регистрируете пользователь заново с другим паролем (если никнейм свободен).
- `scripts\smoke_test.py` использует **отдельный** файл `.smoke_test.db` и не затрагивает
  рабочую базу для разработки.

## TypeScript-клиент для фронтенда

Лежит в `frontend/src/api/`:

- `types.ts`  — DTO и типы запросов/ответов
- `client.ts` — fetch-обёртка, токен в `localStorage`, `ApiError`
- `api.ts`    — `authApi`, `usersApi`, `chatsApi`, `messagesApi`, `notificationsApi`

Базовый URL читается из `VITE_API_BASE_URL` (по умолчанию
`http://localhost:8000/api/v1`). Чтобы переопределить, создайте
`frontend/.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```
