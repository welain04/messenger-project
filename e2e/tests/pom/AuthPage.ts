import { Locator, Page, expect } from "@playwright/test";

/** Page Object для страницы входа/регистрации (/auth). */
export class AuthPage {
  readonly page: Page;
  // Селекторы выбраны устойчиво (по типу/атрибуту/placeholder), без зависимости
  // от вёрстки. Поле никнейма уникально определяется атрибутом pattern.
  readonly nickname: Locator;
  readonly password: Locator;
  readonly email: Locator;
  readonly firstName: Locator;
  readonly lastName: Locator;

  readonly loginTab: Locator;
  readonly registerTab: Locator;
  readonly loginSubmit: Locator;
  readonly registerSubmit: Locator;

  readonly submit: Locator;

  constructor(page: Page) {
    this.page = page;
    // Локаторы по data-testid — устойчивы к изменению вёрстки/текста.
    this.nickname = page.getByTestId("auth-nickname");
    this.password = page.getByTestId("auth-password");
    this.email = page.getByTestId("auth-email");
    this.firstName = page.getByTestId("auth-first-name");
    this.lastName = page.getByTestId("auth-last-name");

    this.loginTab = page.getByTestId("auth-tab-login");
    this.registerTab = page.getByTestId("auth-tab-register");
    // Кнопка отправки одна; режим различаем по наличию полей регистрации.
    this.submit = page.getByTestId("auth-submit");
    this.loginSubmit = this.submit;
    this.registerSubmit = this.submit;
  }

  async goto(): Promise<void> {
    await this.page.goto("/auth");
    await expect(this.submit).toBeVisible();
  }

  async openRegister(): Promise<void> {
    await this.registerTab.click();
    // В режиме регистрации появляется поле email — ждём его.
    await expect(this.email).toBeVisible();
  }

  async openLogin(): Promise<void> {
    await this.loginTab.click();
    // В режиме входа полей регистрации (email) нет.
    await expect(this.email).toHaveCount(0);
  }

  async fillRegister(data: {
    nickname?: string;
    firstName?: string;
    lastName?: string;
    email?: string;
    password?: string;
  }): Promise<void> {
    if (data.nickname !== undefined) await this.nickname.fill(data.nickname);
    if (data.firstName !== undefined) await this.firstName.fill(data.firstName);
    if (data.lastName !== undefined) await this.lastName.fill(data.lastName);
    if (data.email !== undefined) await this.email.fill(data.email);
    if (data.password !== undefined) await this.password.fill(data.password);
  }

  async fillLogin(data: { nickname?: string; password?: string }): Promise<void> {
    if (data.nickname !== undefined) await this.nickname.fill(data.nickname);
    if (data.password !== undefined) await this.password.fill(data.password);
  }

  /** Полный вход через UI с ожиданием перехода к чатам. */
  async login(nickname: string, password: string): Promise<void> {
    await this.openLogin();
    await this.fillLogin({ nickname, password });
    await this.loginSubmit.click();
    await this.page.waitForURL("**/chats");
  }

  /** Попытка входа, ожидаемо неуспешная (остаёмся на /auth). */
  async loginExpectingError(nickname: string, password: string): Promise<void> {
    await this.openLogin();
    await this.fillLogin({ nickname, password });
    await this.loginSubmit.click();
  }

  /** Текст ошибки сервера (ErrorBox). */
  errorMessage(text: string | RegExp): Locator {
    return this.page.getByText(text);
  }

  /** Проверяет, что поле невалидно по нативной HTML5-валидации. */
  async expectFieldInvalid(field: Locator): Promise<void> {
    const valid = await field.evaluate(
      (el: HTMLInputElement) => el.validity.valid,
    );
    expect(valid).toBe(false);
  }

  async expectFieldValid(field: Locator): Promise<void> {
    const valid = await field.evaluate(
      (el: HTMLInputElement) => el.validity.valid,
    );
    expect(valid).toBe(true);
  }
}
