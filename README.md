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
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API будет доступен на `http://127.0.0.1:8000`.

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

По умолчанию E2E поднимают изолированные backend/frontend автоматически (порты `8081` и `5183`), отдельная БД — `backend/e2e.db`.

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