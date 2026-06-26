/**
 * Управление сессией в браузере: «вход» через установку токенов в localStorage.
 *
 * Это позволяет готовить авторизацию через API (быстро и стабильно), а UI
 * использовать только для проверки сценария. Токены кладём в те же ключи
 * localStorage, что использует фронтенд (см. frontend/src/api/client.ts).
 */

import { Browser, BrowserContext, Page, expect } from "@playwright/test";
import { ACCESS_TOKEN_KEY, APP_BASE_URL, REFRESH_TOKEN_KEY } from "./config";
import { BackendApi, TokenPair } from "./backend";

/** Записывает токены в localStorage текущего origin. */
export async function applySession(page: Page, tokens: TokenPair): Promise<void> {
  // localStorage привязан к origin — сначала открываем публичную страницу.
  await page.goto("/auth");
  await page.evaluate(
    ([access, refresh, accessKey, refreshKey]) => {
      localStorage.setItem(accessKey, access);
      localStorage.setItem(refreshKey, refresh);
    },
    [tokens.access_token, tokens.refresh_token, ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY] as const,
  );
}

/** Логинит пользователя через API и применяет сессию к странице. */
export async function loginAs(
  page: Page,
  api: BackendApi,
  nickname: string,
  password: string,
): Promise<void> {
  const tokens = await api.login(nickname, password);
  await applySession(page, tokens);
}

/**
 * Открывает приложение во ВТОРОМ изолированном контексте под другим
 * пользователем (нужно, чтобы проверить отображение у обоих участников чата).
 * Вызывающая сторона обязана закрыть возвращённый context.
 */
export async function openSecondUser(
  browser: Browser,
  api: BackendApi,
  nickname: string,
  password: string,
): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext({ baseURL: APP_BASE_URL });
  const page = await context.newPage();
  await loginAs(page, api, nickname, password);
  return { context, page };
}

/** Открывает приложение под пользователем и ждёт готовности (никнейм в шапке). */
export async function openAppAs(
  page: Page,
  api: BackendApi,
  nickname: string,
  password: string,
  gotoPath = "/chats",
): Promise<void> {
  await loginAs(page, api, nickname, password);
  await page.goto(gotoPath);
  await expect(page.getByText(nickname, { exact: true })).toBeVisible();
}
