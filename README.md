# Online School Messenger

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

## Конфигурация и безопасность

Все параметры задаются через переменные окружения / `backend/.env`
(полный список с комментариями — в `backend/.env.example`). Ключевые из них:

| Переменная | Назначение |
|---|---|
| `APP_ENV` | `development` \| `production` \| `test`. В `production` включаются жёсткие проверки конфигурации. |
| `JWT_SECRET` | Секрет подписи JWT. Сгенерировать: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. |
| `CORS_ORIGINS` | Белый список origin'ов фронтенда через запятую (не `*`). |
| `ENABLE_TEST_ENDPOINTS` | Тестовые ручки `/api/v1/_test/*` (только для E2E). В production должно быть `false`. |
| `RATE_LIMIT_*_PER_MIN` | Лимиты запросов в минуту на IP (`0` — выключено). |
| `TRUST_PROXY_HEADERS` / `TRUSTED_PROXY_COUNT` | Учитывать `X-Forwarded-For` за обратным прокси (включать только за доверенным прокси). |
| `STORAGE_PROVIDER` | `local` (dev) или `yandex` (Yandex Object Storage). |
| `AVATAR_MAX_BYTES` / `ATTACHMENT_MAX_BYTES` / `ALLOWED_*_MIMES` | Лимиты размера и белый список типов загружаемых файлов. |

Что уже реализовано «из коробки»:

- **SQL-инъекции** — все запросы параметризованы.
- **XSS** — пользовательский текст рендерится через JSX (автоэкранирование React), без `dangerouslySetInnerHTML`.
- **CORS** — белый список origin'ов, суженные методы и заголовки.
- **Rate limit** — на логин, регистрацию, refresh, подтверждение email и сброс пароля.
- **Ошибки** — наружу без stack trace; ошибки валидации — человекочитаемые сообщения.
- **Загрузка файлов** — проверка размера и реального типа по содержимому (magic bytes), а не только по `Content-Type`.
- **Защита конфигурации** — в `production` приложение не стартует со слабым `JWT_SECRET` или с включёнными тестовыми эндпоинтами.

### Чек-лист перед продакшеном

1. `APP_ENV=production` и стойкий `JWT_SECRET` в `.env`.
2. `CORS_ORIGINS` — реальный домен фронтенда (например `https://app.example.com`).
3. `ENABLE_TEST_ENDPOINTS=false`.
4. За обратным прокси (nginx): `TRUST_PROXY_HEADERS=true`, корректный `TRUSTED_PROXY_COUNT`
   и `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`.
5. Боевые `STORAGE_PROVIDER`/S3-ключи и `SMTP_*` заданы и не закоммичены.
6. (При нескольких воркерах/инстансах) вынести rate limit в Redis — общий счётчик.

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