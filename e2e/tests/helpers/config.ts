/** Базовые URL тестовой среды (совпадают с playwright.config.ts). */

// Должны совпадать с портами из playwright.config.ts (изолированы от dev).
export const APP_BASE_URL = process.env.APP_BASE_URL ?? "http://127.0.0.1:5183";
export const API_BASE_URL = process.env.API_BASE_URL ?? "http://127.0.0.1:8081/api/v1";

/** Пароль по умолчанию для тестовых пользователей. */
export const DEFAULT_PASSWORD = "Password123";

/** Ключи localStorage, которые использует фронтенд для хранения токенов. */
export const ACCESS_TOKEN_KEY = "messenger.token";
export const REFRESH_TOKEN_KEY = "messenger.refresh";
