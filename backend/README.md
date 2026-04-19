# Online School Messenger — Backend

FastAPI-бэкенд мессенджера онлайн-школы. Хранение данных — в памяти (Python `dict`),
без БД. Авторизация — JWT (HS256), пароли — bcrypt (passlib).

## Структура

```
backend/
  app/
    __init__.py
    config.py          # Settings (BaseSettings, читает .env)
    main.py            # create_app(), CORS, JWT-middleware, /api/v1
    middleware.py      # JWTUserMiddleware -> request.state.user
    deps.py            # get_current_user / get_current_user_or_none
    security.py        # хеш паролей, create/decode JWT
    storage.py         # in-memory хранилище + индексы + lock
    models.py          # dataclass-модели UserInDB, Chat, Message, Notification
    schemas.py         # Pydantic-схемы запросов/ответов
    routers/
      auth.py
      users.py
      chats.py
      messages.py
      notifications.py
  scripts/
    export_openapi.py  # пишет openapi.json
    smoke_test.py      # сквозной TestClient-сценарий
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

| Имя                          | Назначение                                 | По умолчанию                                                |
|------------------------------|--------------------------------------------|-------------------------------------------------------------|
| `JWT_SECRET`                 | секрет подписи JWT                         | `change-me`                                                 |
| `JWT_ALGORITHM`              | алгоритм JWT                               | `HS256`                                                     |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| TTL access-токена в минутах                | `1440`                                                      |
| `CORS_ORIGINS`               | разрешённые origin'ы через запятую         | `http://localhost:5173,http://127.0.0.1:5173`               |
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

## Полезные скрипты

```powershell
# Регенерировать openapi.json:
.\.venv\Scripts\python.exe scripts\export_openapi.py

# Прогон сквозного smoke-теста:
.\.venv\Scripts\python.exe scripts\smoke_test.py
```

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
