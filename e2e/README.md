# E2E-тесты (Playwright) — Online School Messenger

End-to-end тесты пользовательских сценариев мессенджера. Playwright сам
поднимает backend (FastAPI) и frontend (Vite) в изолированной тестовой среде,
готовит данные через API и проверяет сценарии через UI.

## Требования

- Node.js 18+
- Python 3.11+ с настроенным виртуальным окружением backend в `../backend/.venv`
  и установленными зависимостями (`pip install -r ../backend/requirements.txt`).

## Установка

```bash
cd e2e
npm install
npm run test:e2e:install   # установка браузера Chromium для Playwright
```

## Запуск

```bash
npm run test:e2e          # прогон всех тестов (headless)
npm run test:e2e:ui       # интерактивный UI-режим Playwright
npm run test:e2e:headed   # прогон в видимом браузере
npm run test:e2e:report   # открыть HTML-отчёт последнего прогона
```

Запускать отдельный сценарий:

```bash
npx playwright test 03-password-recovery
```

## Как это устроено

Playwright перед тестами запускает два сервера (см. `playwright.config.ts`):

| Сервер   | URL                          | Особенности тестовой среды |
|----------|------------------------------|----------------------------|
| backend  | `http://127.0.0.1:8081`      | отдельная БД `backend/e2e.db`, локальное файловое хранилище, без SMTP, без rate limit, включены `/_test/*` |
| frontend | `http://127.0.0.1:5183`      | Vite в режиме `--mode test`, `VITE_API_BASE_URL` указывает на backend `:8081` |

Порты намеренно отличаются от dev (5173/8000), поэтому E2E можно запускать,
не останавливая обычные серверы разработки. Рабочая БД `messenger.db` не
затрагивается.

### Тестовые токены (email-потоки)

SMTP в тестах отключён (`SMTP_HOST=""`). Письма попадают во внутренний
`mailer.outbox`. Backend в тестовой среде поднимает вспомогательные эндпоинты
(только при `ENABLE_TEST_ENDPOINTS=1`):

- `POST /api/v1/_test/users` — создать пользователя с нужной ролью и
  подтверждённым email (фабрика данных);
- `GET /api/v1/_test/emails/last?email=...` — получить последний токен
  (verification / reset) для адреса.

Эти эндпоинты **выключены** по умолчанию и недоступны в production.

### Ручной запуск backend в тест-режиме

Playwright подставляет переменные окружения сам. Для ручного запуска backend в
той же конфигурации есть шаблон `backend/.env.test.example`:

```bash
cd ../backend
cp .env.test.example .env.test
ENV_FILE=.env.test python -m uvicorn app.main:app --port 8081
```

(`config.py` читает файл из `ENV_FILE`, по умолчанию `.env`.)

## Структура

```
e2e/
├─ playwright.config.ts          # конфиг + запуск backend/frontend
├─ tests/
│  ├─ e2e/                       # по одному файлу на сценарий
│  │  ├─ 01-registration-and-validation.spec.ts
│  │  ├─ 02-change-avatar.spec.ts
│  │  ├─ 03-password-recovery.spec.ts
│  │  ├─ 04-profile-edit.spec.ts
│  │  ├─ 05-student-delete-restrictions.spec.ts
│  │  ├─ 06-unread-and-notifications.spec.ts
│  │  ├─ 07-student-creates-chats.spec.ts
│  │  └─ 08-curator-rights.spec.ts
│  ├─ fixtures/
│  │  └─ test.ts                 # фикстуры: api, users (фабрика), POM
│  ├─ helpers/
│  │  ├─ backend.ts              # обёртка над REST API (подготовка данных)
│  │  ├─ session.ts              # вход через localStorage, второй пользователь
│  │  ├─ config.ts               # базовые URL и ключи токенов
│  │  └─ unique.ts               # генерация уникальных никнеймов/email/текстов
│  ├─ data/
│  │  └─ files.ts                # in-memory файлы (валидный PNG, невалидный txt)
│  └─ pom/                       # Page Object Model
│     ├─ AuthPage.ts
│     ├─ ProfilePage.ts
│     ├─ ChatsPage.ts
│     ├─ ChatPage.ts
│     └─ PasswordRecoveryPages.ts
└─ README.md
```

## Принципы

- **Данные через API, проверки через UI.** Пользователи, чаты и сообщения
  готовятся вызовами REST API; UI используется для проверки самого сценария.
- **Независимость.** Каждый тест создаёт собственных пользователей с
  уникальными никнеймами/email (`helpers/unique.ts`), поэтому тесты не зависят
  от seed-данных и друг от друга, и их можно запускать параллельно.
- **Устойчивые ожидания.** Используются web-first assertions Playwright
  (`expect(locator).toBeVisible()` и т.п.) и `waitForURL`. Нет `sleep` и
  фиксированных таймаутов-заглушек.
- **Селекторы по `data-testid`.** POM используют `getByTestId(...)` для
  устойчивости к изменению вёрстки и текста. Текст (`getByText`) применяется
  только там, где проверяется реальный контент (текст сообщения/ошибки/
  уведомления). Перечень testid: `auth-*`, `profile-*`, `chats-*`, `chat-*`,
  `unread-badge`, `notification-item`, `notification-message`.
- **Русские названия** `describe`/`test` и шаги `test.step()`.
