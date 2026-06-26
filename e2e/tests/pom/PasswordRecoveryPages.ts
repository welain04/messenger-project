import { Locator, Page, expect } from "@playwright/test";

/** Page Object для запроса восстановления пароля (/forgot-password). */
export class ForgotPasswordPage {
  readonly page: Page;
  readonly email: Locator;
  readonly submit: Locator;

  constructor(page: Page) {
    this.page = page;
    this.email = page.locator('input[type="email"]');
    this.submit = page.getByRole("button", { name: "Отправить ссылку" });
  }

  async goto(): Promise<void> {
    await this.page.goto("/forgot-password");
    await expect(this.submit).toBeVisible();
  }

  async requestReset(email: string): Promise<void> {
    await this.email.fill(email);
    await this.submit.click();
  }
}

/** Page Object для установки нового пароля по токену (/reset-password). */
export class ResetPasswordPage {
  readonly page: Page;
  readonly password: Locator;
  readonly confirm: Locator;
  readonly submit: Locator;

  constructor(page: Page) {
    this.page = page;
    this.password = page.locator('input[type="password"]').nth(0);
    this.confirm = page.locator('input[type="password"]').nth(1);
    this.submit = page.getByRole("button", { name: "Сохранить пароль" });
  }

  async goto(token: string): Promise<void> {
    await this.page.goto(`/reset-password?token=${token}`);
    await expect(this.submit).toBeVisible();
  }

  async setNewPassword(password: string, confirm?: string): Promise<void> {
    await this.password.fill(password);
    await this.confirm.fill(confirm ?? password);
    await this.submit.click();
  }
}
