import { Locator, Page, expect } from "@playwright/test";
import { InMemoryFile } from "../data/files";

/** Page Object для страницы профиля (/profile). */
export class ProfilePage {
  readonly page: Page;
  readonly avatarFileInput: Locator;
  readonly avatarDeleteButton: Locator;
  readonly nicknameInput: Locator;
  readonly saveNicknameButton: Locator;

  // Форма смены пароля.
  readonly currentPassword: Locator;
  readonly newPassword: Locator;
  readonly confirmPassword: Locator;
  readonly updatePasswordButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.avatarFileInput = page.getByTestId("profile-avatar-input");
    this.avatarDeleteButton = page.getByTestId("profile-avatar-delete");
    this.nicknameInput = page.getByTestId("profile-nickname-input");
    this.saveNicknameButton = page.getByTestId("profile-nickname-save");

    this.currentPassword = page.getByTestId("profile-password-current");
    this.newPassword = page.getByTestId("profile-password-new");
    this.confirmPassword = page.getByTestId("profile-password-confirm");
    this.updatePasswordButton = page.getByTestId("profile-password-submit");
  }

  async goto(): Promise<void> {
    await this.page.goto("/profile");
    await expect(this.page.getByRole("heading", { name: "Аватар" })).toBeVisible();
  }

  /** Аватар-картинка в шапке профиля (рендерится <img>, когда есть аватар). */
  avatarImage(fullName: string): Locator {
    return this.page.locator(`img[aria-label="${fullName}"]`);
  }

  /** Сообщение об ошибке загрузки аватара (ErrorBox). */
  avatarError(text: string | RegExp): Locator {
    return this.page.getByText(text);
  }

  /** Аватар отображается картинкой (а не инициалами) — появляется кнопка «Удалить». */
  async expectAvatarPresent(): Promise<void> {
    await expect(this.avatarDeleteButton).toBeVisible();
  }

  async expectAvatarAbsent(): Promise<void> {
    await expect(this.avatarDeleteButton).toHaveCount(0);
  }

  async uploadAvatar(file: InMemoryFile): Promise<void> {
    await this.avatarFileInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });
  }

  async changeNickname(newNickname: string): Promise<void> {
    await this.nicknameInput.fill(newNickname);
    await this.saveNicknameButton.click();
  }

  async changePassword(current: string, next: string, confirm?: string): Promise<void> {
    await this.currentPassword.fill(current);
    await this.newPassword.fill(next);
    await this.confirmPassword.fill(confirm ?? next);
    await this.updatePasswordButton.click();
  }
}
