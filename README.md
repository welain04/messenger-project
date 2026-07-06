# Online School Messenger

[![CI](https://github.com/welain04/messenger-project/actions/workflows/ci.yml/badge.svg)](https://github.com/welain04/messenger-project/actions/workflows/ci.yml)

Монорепозиторий учебного мессенджера:
- `backend/` — FastAPI + SQLite
- `frontend/` — React 18 + TypeScript + Vite
- `e2e/` — Playwright E2E-тесты

## Быстрый старт

### 1) Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # затем отредактируйте .env (как минимум JWT_SECRET)
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен на `http://127.0.0.1:8000`.

Конфигурация читается из `backend/.env` (см. шаблон `backend/.env.example`).
Файл `.env` в `.gitignore` и в репозиторий не попадает.

### 2) Frontend

```powershell
cd frontend
npm install
npm run dev
```

Приложение будет доступно на `http://127.0.0.1:5173`.

Конфигурация фронтенда: шаблон `frontend/.env.example` (`VITE_API_BASE_URL`).
Для локальной разработки fallback задан в коде (`http://localhost:8000/api/v1`).

## Первый администратор (без очистки БД)

Для production и staging используйте отдельный скрипт — **не** `scripts/seed.py`
(он полностью стирает базу и создаёт тестовых пользователей с паролем `password123`):

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\create_admin.py --nickname admin --email admin@school.ru
```

Пароль: аргумент `--password`, переменная `ADMIN_PASSWORD` или интерактивный ввод.
Если в базе уже есть активный admin, скрипт завершится с ошибкой (используйте `--force`
для добавления ещё одного).

## E2E (Playwright)

### Подготовка (один раз)

```powershell
cd e2e
npm install
npm run test:e2e:install
```

### Основные команды

```powershell
cd e2e
npm run test:e2e          # все тесты (headless)
npm run test:e2e:headed   # видимый браузер
npm run test:e2e:ui       # Playwright UI
npm run test:e2e:report   # HTML-отчёт
```

По умолчанию E2E поднимают изолированные backend/frontend автоматически (порты `8081` и `5183`), отдельная БД — `backend/e2e.db`, локальное файловое хранилище (без Yandex S3), без SMTP и без rate limit. Прод-`.env` при этом не используется.

## CI (GitHub Actions)

Конфигурация: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

Workflow **CI** запускается автоматически при каждом **push** (любая ветка) и при **pull request**. Секреты и prod-`.env` не нужны — проверки используют изолированные тестовые настройки. При новом push в ту же ветку предыдущий прогон отменяется.

Три job'а выполняются **параллельно**:

| Job | Что проверяет |
|---|---|
| **Backend (smoke test)** | Python 3.12, `pip install`, скрипт `backend/scripts/smoke_test.py` (регистрация, чаты, сообщения, права через `TestClient`) |
| **Frontend (typecheck & build)** | Node 20, `npm ci`, `tsc --noEmit`, `vite build` |
| **E2E (Playwright)** | Полный прогон Playwright: backend/frontend поднимаются автоматически (`CI=true` → 1 worker, 1 retry) |

Результаты: вкладка **Actions** в GitHub. Если упал job **E2E**, скачайте артефакт `playwright-report` (HTML-отчёт, хранится 7 дней).

### Локально повторить проверки CI

**Backend (smoke test):**

```powershell
cd backend
python -m pip install -r requirements.txt
$env:APP_ENV="development"
$env:SMTP_HOST=""
$env:DATABASE_PATH=".smoke_test.db"
$env:RATE_LIMIT_LOGIN_PER_MIN="0"
$env:RATE_LIMIT_REGISTER_PER_MIN="0"
$env:RATE_LIMIT_SEARCH_PER_MIN="0"
$env:RATE_LIMIT_VERIFY_PER_MIN="0"
$env:RATE_LIMIT_FORGOT_PASSWORD_PER_MIN="0"
$env:RATE_LIMIT_RESET_PASSWORD_PER_MIN="0"
python scripts/smoke_test.py
```

Linux / macOS:

```bash
cd backend
pip install -r requirements.txt
APP_ENV=development SMTP_HOST= DATABASE_PATH=.smoke_test.db \
  RATE_LIMIT_LOGIN_PER_MIN=0 RATE_LIMIT_REGISTER_PER_MIN=0 \
  RATE_LIMIT_SEARCH_PER_MIN=0 RATE_LIMIT_VERIFY_PER_MIN=0 \
  RATE_LIMIT_FORGOT_PASSWORD_PER_MIN=0 RATE_LIMIT_RESET_PASSWORD_PER_MIN=0 \
  python scripts/smoke_test.py
```

**Frontend (typecheck & build):**

```powershell
cd frontend
npm ci
npx tsc --noEmit
$env:VITE_API_BASE_URL="http://127.0.0.1:8081/api/v1"
npm run build
```

**E2E (как в CI):**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
cd ..\frontend
npm ci
cd ..\e2e
npm ci
npm run test:e2e:install
$env:CI="true"
npm run test:e2e
```

## Конфигурация и безопасность

Все параметры задаются через переменные окружения / `backend/.env`
(полный список с комментариями — в `backend/.env.example`). Ключевые из них:

| Переменная | Назначение |
|---|---|
| `APP_ENV` | `development` \| `production` \| `test`. В `production` включаются жёсткие проверки конфигурации. |
| `JWT_SECRET` | Секрет подписи JWT. Сгенерировать: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. |
| `CORS_ORIGINS` | Белый список origin'ов фронтенда через запятую (не `*`). |
| `ENABLE_TEST_ENDPOINTS` | Тестовые ручки `/api/v1/_test/*` (только для E2E). В production должно быть `false`. |
| `ALLOW_PUBLIC_REGISTRATION` | Открытая регистрация (`false` — invite-only, 403 на register). |
| `RATE_LIMIT_*_PER_MIN` | Лимиты запросов в минуту на IP (`0` — выключено), в т.ч. `RESET_PASSWORD`. |
| `RATE_LIMIT_BACKEND` | `memory` (один процесс) или `redis` (заготовка для масштабирования). |
| `TRUST_PROXY_HEADERS` / `TRUSTED_PROXY_COUNT` | Учитывать `X-Forwarded-For` за обратным прокси (включать только за доверенным прокси). |
| `STORAGE_PROVIDER` | `local` (dev) или `yandex` (Yandex Object Storage). |
| `AVATAR_MAX_BYTES` / `ATTACHMENT_MAX_BYTES` / `ALLOWED_*_MIMES` | Лимиты размера и белый список типов загружаемых файлов. |

Что уже реализовано «из коробки»:

- **SQL-инъекции** — все запросы параметризованы.
- **XSS** — пользовательский текст рендерится через JSX (автоэкранирование React), без `dangerouslySetInnerHTML`.
- **CORS** — белый список origin'ов, суженные методы и заголовки.
- **Rate limit** — на логин, регистрацию, refresh, подтверждение email, запрос и сброс пароля; бэкенд `memory`/`redis`.
- **Пароли** — минимум 8 символов, буква и цифра.
- **Email verification** — мессенджер (чаты, сообщения, уведомления, файлы) доступен только с подтверждённым email.
- **Сессии** — access-токен проверяется по `sid`; отозванная сессия недействительна сразу.
- **Регистрация** — по умолчанию открытая; `ALLOW_PUBLIC_REGISTRATION=false` для закрытой школы.
- **Security headers** — в production автоматически (`X-Frame-Options`, `X-Content-Type-Options` и др.).
- **Ошибки** — наружу без stack trace; ошибки валидации — человекочитаемые сообщения.
- **Загрузка файлов** — проверка размера и реального типа по содержимому (magic bytes), а не только по `Content-Type`.
- **Защита конфигурации** — в `production` приложение не стартует со слабым `JWT_SECRET`,
  с включёнными тестовыми эндпоинтами, без SMTP, с `local`-хранилищем или с localhost в URL.
  Отключаются `/docs`, `/redoc`, `/openapi.json`, `/test`.

### Чек-лист перед продакшеном

1. `APP_ENV=production` и стойкий `JWT_SECRET` в `.env` (см. секцию 2 в `backend/.env.example`).
2. `CORS_ORIGINS` и `FRONTEND_BASE_URL` — реальные публичные домены (без localhost).
3. `ENABLE_TEST_ENDPOINTS=false`.
4. `SMTP_HOST` и учётные данные SMTP заданы.
5. `STORAGE_PROVIDER=yandex` и заполнены `S3_*`.
6. Сборка фронтенда с `VITE_API_BASE_URL` (см. `frontend/.env.example`).
7. Первый admin: `backend/scripts/create_admin.py` (не `seed.py`).
8. За обратным прокси (nginx): `TRUST_PROXY_HEADERS=true`, корректный `TRUSTED_PROXY_COUNT`
   и `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`.
9. (При нескольких воркерах/инстансах) вынести rate limit в Redis — общий счётчик.

### Демонстрационный медленный прогон (slowMo)

В репозитории есть временный конфиг: `e2e/playwright.slowmo.config.ts`.

Пример запуска одного сценария в видимом браузере:

```powershell
cd e2e
npx playwright test tests/e2e/03-password-recovery.spec.ts --headed --workers=1 --config=playwright.slowmo.config.ts
```

### HTML-отчёт (если localhost не открывается)

```powershell
cd e2e
npx playwright show-report --host 127.0.0.1 --port 9323
```

Открыть: `http://127.0.0.1:9323`.