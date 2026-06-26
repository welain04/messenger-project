import { Locator, Page, expect } from "@playwright/test";
import { InMemoryFile } from "../data/files";

/** Page Object для страницы конкретного чата (/chats/:chatId). */
export class ChatPage {
  readonly page: Page;
  readonly messageInput: Locator;
  readonly sendButton: Locator;
  readonly attachInput: Locator;
  readonly membersToggle: Locator;
  readonly addMemberInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.messageInput = page.getByTestId("chat-message-input");
    this.sendButton = page.getByTestId("chat-send-button");
    this.attachInput = page.getByTestId("chat-attach-input");
    this.membersToggle = page.getByTestId("chat-members-toggle");
    this.addMemberInput = page.getByTestId("chat-add-member-input");
  }

  async goto(chatId: string): Promise<void> {
    await this.page.goto(`/chats/${chatId}`);
    await expect(this.messageInput).toBeVisible();
  }

  /** Контейнер «пузыря» сообщения по его тексту. */
  bubble(text: string): Locator {
    return this.page.getByTestId("chat-message").filter({ hasText: text });
  }

  deleteButtonOf(text: string): Locator {
    return this.bubble(text).getByTestId("chat-delete-message");
  }

  async sendText(text: string): Promise<void> {
    await this.messageInput.fill(text);
    await this.sendButton.click();
    // Проверяем именно «пузырь» сообщения, а не превью последнего сообщения
    // в боковой панели (там тот же текст).
    await expect(this.bubble(text).first()).toBeVisible();
  }

  async attachImageAndSend(file: InMemoryFile, text?: string): Promise<void> {
    await this.attachInput.setInputFiles({
      name: file.name,
      mimeType: file.mimeType,
      buffer: file.buffer,
    });
    // Дожидаемся «чипа» прикреплённого файла перед отправкой.
    await expect(this.page.getByText(file.name)).toBeVisible();
    if (text) await this.messageInput.fill(text);
    await this.sendButton.click();
  }

  attachmentImage(fileName: string): Locator {
    return this.page.locator(`img[alt="${fileName}"]`);
  }

  /** Вложение-изображение отрисовано и доступно (есть непустой src). */
  async expectAttachmentVisible(fileName: string): Promise<void> {
    const img = this.attachmentImage(fileName);
    await expect(img).toBeVisible();
    await expect(img).toHaveJSProperty("complete", true);
    const src = await img.getAttribute("src");
    expect(src && src.length > 0).toBeTruthy();
  }

  async expectMessageVisible(text: string): Promise<void> {
    await expect(this.bubble(text).first()).toBeVisible();
  }

  async expectMessageAbsent(text: string): Promise<void> {
    await expect(this.bubble(text)).toHaveCount(0);
  }

  async expectCanDelete(text: string): Promise<void> {
    await expect(this.deleteButtonOf(text)).toHaveCount(1);
  }

  async expectCannotDelete(text: string): Promise<void> {
    await expect(this.bubble(text).first()).toBeVisible();
    await expect(this.deleteButtonOf(text)).toHaveCount(0);
  }

  /** Удаляет сообщение по тексту (для тех, у кого есть право удаления). */
  async deleteMessage(text: string): Promise<void> {
    const bubble = this.bubble(text).first();
    await bubble.hover();
    await this.deleteButtonOf(text).first().click();
    const dialog = this.page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Удалить" }).click();
    await this.expectMessageAbsent(text);
  }

  /** Удаляет собственное сообщение (псевдоним deleteMessage для читаемости). */
  async deleteOwnMessage(text: string): Promise<void> {
    await this.deleteMessage(text);
  }

  async openMembers(): Promise<void> {
    await this.membersToggle.click();
    await expect(this.addMemberInput).toBeVisible();
  }

  memberRow(nickname: string): Locator {
    return this.page.getByTestId("chat-member-row").filter({ hasText: `@${nickname}` });
  }

  async expectMemberPresent(nickname: string): Promise<void> {
    await expect(this.memberRow(nickname)).toHaveCount(1);
  }

  async expectMemberAbsent(nickname: string): Promise<void> {
    await expect(this.memberRow(nickname)).toHaveCount(0);
  }

  async addMember(nickname: string): Promise<void> {
    await this.addMemberInput.fill(nickname);
    const result = this.page
      .getByTestId("chat-add-member-result")
      .filter({ hasText: `@${nickname}` });
    await expect(result).toBeVisible();
    await result.click();
    await this.expectMemberPresent(nickname);
  }

  async removeMember(nickname: string): Promise<void> {
    const row = this.memberRow(nickname);
    await row.hover();
    await row.getByTestId("chat-remove-member").click();
    const dialog = this.page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Удалить" }).click();
    await this.expectMemberAbsent(nickname);
  }
}
