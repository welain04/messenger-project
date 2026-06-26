import { Locator, Page, expect } from "@playwright/test";

/** Page Object для страницы списка чатов и формы создания чата (/chats). */
export class ChatsPage {
  readonly page: Page;
  readonly typeSelect: Locator;
  readonly titleInput: Locator;
  readonly searchInput: Locator;
  readonly createButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.typeSelect = page.getByTestId("chats-type-select");
    this.titleInput = page.getByTestId("chats-title-input");
    this.searchInput = page.getByTestId("chats-participant-search");
    this.createButton = page.getByTestId("chats-create-button");
  }

  async goto(): Promise<void> {
    await this.page.goto("/chats");
    await expect(this.createButton).toBeVisible();
  }

  /** Найти пользователя по никнейму и добавить его в список участников. */
  private async pickParticipant(nickname: string): Promise<void> {
    await this.searchInput.fill(nickname);
    const result = this.page
      .getByTestId("chats-search-result")
      .filter({ hasText: `@${nickname}` });
    await expect(result).toBeVisible();
    await result.click();
    // После выбора появляется «чип» участника, а поиск очищается.
    await expect(this.page.getByText(`@${nickname}`)).toBeVisible();
  }

  private chatIdFromUrl(): string {
    const url = this.page.url();
    const id = url.split("/chats/")[1];
    return id;
  }

  async createPersonalChat(nickname: string): Promise<string> {
    await this.typeSelect.selectOption({ label: "Личный" });
    await this.pickParticipant(nickname);
    await this.createButton.click();
    await this.page.waitForURL(/\/chats\/[0-9a-fA-F-]{8,}/);
    return this.chatIdFromUrl();
  }

  async createGroupChat(title: string, nicknames: string[]): Promise<string> {
    await this.typeSelect.selectOption({ label: "Групповой" });
    await this.titleInput.fill(title);
    for (const nick of nicknames) {
      await this.pickParticipant(nick);
    }
    await this.createButton.click();
    await this.page.waitForURL(/\/chats\/[0-9a-fA-F-]{8,}/);
    return this.chatIdFromUrl();
  }
}
