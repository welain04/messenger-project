import { defineConfig, devices } from "@playwright/test";
import * as path from "path";
import * as os from "os";

/**
 * Конфигурация Playwright для Online School Messenger.
 *
 * Перед тестами автоматически поднимаются ДВА сервера (см. `webServer`):
 *   1) backend (FastAPI / uvicorn) на http://127.0.0.1:8081
 *   2) frontend (Vite dev) на http://127.0.0.1:5183
 *
 * Backend запускается в ИЗОЛИРОВАННОЙ тестовой среде:
 *   - отдельная БД SQLite (e2e.db) — рабочая messenger.db не затрагивается;
 *   - локальное файловое хранилище (STORAGE_PROVIDER=local) — без Yandex S3;
 *   - письма не уходят по SMTP, а пишутся в in-memory outbox (SMTP_HOST="");
 *   - включены тестовые эндпоинты /api/v1/_test/* (ENABLE_TEST_ENDPOINTS=1);
 *   - отключён rate limiting (RATE_LIMIT_* = 0).
 */

// Выделенные порты для E2E, чтобы НЕ конфликтовать с dev-серверами
// разработчика (которые обычно занимают 5173 и 8000).
const APP_PORT = 5183;
const API_PORT = 8081;

export const APP_BASE_URL = `http://127.0.0.1:${APP_PORT}`;
export const API_BASE_URL = `http://127.0.0.1:${API_PORT}/api/v1`;

const repoRoot = path.resolve(__dirname, "..");
const backendDir = path.join(repoRoot, "backend");
const frontendDir = path.join(repoRoot, "frontend");

// Путь к python из виртуального окружения backend.
const pythonPath =
  os.platform() === "win32"
    ? path.join(backendDir, ".venv", "Scripts", "python.exe")
    : path.join(backendDir, ".venv", "bin", "python");

// Изолированные артефакты тестовой среды backend.
const e2eDbPath = path.join(backendDir, "e2e.db");

const backendEnv: Record<string, string> = {
  APP_ENV: "test",
  ENABLE_TEST_ENDPOINTS: "1",
  DATABASE_PATH: e2eDbPath,
  // Локальное хранилище файлов (аватары/вложения) вместо Yandex S3.
  STORAGE_PROVIDER: "local",
  LOCAL_STORAGE_PATH: "e2e_uploads",
  STORAGE_SERVE_BASE_URL: `http://127.0.0.1:${API_PORT}`,
  // CORS должен разрешать origin тестового фронтенда.
  CORS_ORIGINS: `${APP_BASE_URL},http://localhost:${APP_PORT}`,
  // Пустой SMTP_HOST => письма попадают только в outbox (dev-режим).
  SMTP_HOST: "",
  // Отключаем все лимиты, чтобы повторные логины/регистрации не блокировались.
  RATE_LIMIT_LOGIN_PER_MIN: "0",
  RATE_LIMIT_REGISTER_PER_MIN: "0",
  RATE_LIMIT_SEARCH_PER_MIN: "0",
  RATE_LIMIT_VERIFY_PER_MIN: "0",
  RATE_LIMIT_FORGOT_PASSWORD_PER_MIN: "0",
  // Ссылки в письмах должны вести на тестовый фронтенд.
  FRONTEND_BASE_URL: APP_BASE_URL,
  PYTHONUNBUFFERED: "1",
};

export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./test-results",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : 2,
  reporter: [["list"], ["html", { open: "never" }]],

  timeout: 60_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: APP_BASE_URL,
    actionTimeout: 15_000,
    navigationTimeout: 20_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  webServer: [
    {
      command: `"${pythonPath}" -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: backendDir,
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
      env: backendEnv,
    },
    {
      // `--mode test` => Vite читает frontend/.env.test (VITE_API_BASE_URL -> :8081).
      command: `npm run dev -- --mode test --port ${APP_PORT} --strictPort --host 127.0.0.1`,
      cwd: frontendDir,
      url: APP_BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        VITE_API_BASE_URL: API_BASE_URL,
      },
    },
  ],
});
