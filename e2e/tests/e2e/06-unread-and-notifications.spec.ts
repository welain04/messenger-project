import { test, expect } from "../fixtures/test";
import { loginAs } from "../helpers/session";
import { uniqueMessage } from "../helpers/unique";

test.describe("Сценарий 6: Непрочитанные сообщения и уведомления", () => {
  test("Пользователь получает уведомление о непрочитанном сообщении", async ({
    page,
    api,
    users,
    chatPage,
  }) => {
    const { user: userA, tokens: tokensA } = await users.createWithTokens({ prefix: "unA" });
    const userB = await users.student("unB");
    const messageText = uniqueMessage("unread");

    let chatId = "";
    await test.step("Пользователь A создаёт чат и отправляет сообщение пользователю B", async () => {
      const chat = await api.createPersonalChat(tokensA.access_token, userB.id);
      chatId = chat.id;
      await api.sendMessage(tokensA.access_token, chatId, messageText);
    });

    await test.step("Пользователь B видит непрочитанное сообщение (unread_count)", async () => {
      await loginAs(page, api, userB.nickname, userB.password);
      await page.goto("/chats");
      // Бейдж непрочитанных появляется в боковой панели и в навигации.
      await expect(page.getByTestId("unread-badge").first()).toBeVisible();
      await expect(page.getByLabel("Непрочитанных: 1").first()).toBeVisible();
    });

    await test.step("Появляется уведомление о новом сообщении", async () => {
      await page.goto("/notifications");
      await expect(
        page.getByTestId("notification-message").filter({ hasText: "Новое сообщение" }).first(),
      ).toBeVisible();
    });

    await test.step("После открытия чата непрочитанное исчезает, счётчик обновляется", async () => {
      await chatPage.goto(chatId);
      await chatPage.expectMessageVisible(messageText);
      // Возврат к списку — бейджей непрочитанных больше нет.
      await page.goto("/chats");
      await expect(page.getByTestId("unread-badge")).toHaveCount(0);
    });
  });
});
