import { test } from "../fixtures/test";
import { loginAs, openSecondUser } from "../helpers/session";
import { uniqueMessage } from "../helpers/unique";
import { validImageAttachment } from "../data/files";
import { ChatPage } from "../pom/ChatPage";

test.describe("Сценарий 7: Студент создаёт чаты и отправляет сообщения", () => {
  test("Студент создаёт личный и групповой чат и отправляет сообщения", async ({
    page,
    browser,
    api,
    users,
    chatsPage,
    chatPage,
  }) => {
    // Автор сценария — studentA (через UI). Собеседники готовятся через API.
    const studentA = await users.student("crA");
    const studentB = await users.student("crB");
    const studentC = await users.student("crC");

    await test.step("Входим под studentA", async () => {
      await loginAs(page, api, studentA.nickname, studentA.password);
    });

    await test.step("Личный чат: создание и отправка текстового сообщения", async () => {
      await chatsPage.goto();
      const personalId = await chatsPage.createPersonalChat(studentB.nickname);

      const text = uniqueMessage("personal");
      await chatPage.sendText(text);

      // Сообщение видно у обоих участников.
      await chatPage.expectMessageVisible(text);
      const viewer = await openSecondUser(browser, api, studentB.nickname, studentB.password);
      try {
        const viewerChat = new ChatPage(viewer.page);
        await viewerChat.goto(personalId);
        await viewerChat.expectMessageVisible(text);
      } finally {
        await viewer.context.close();
      }
    });

    await test.step("Групповой чат: создание, текст и вложение-изображение", async () => {
      await chatsPage.goto();
      const groupId = await chatsPage.createGroupChat("Учебная группа", [
        studentB.nickname,
        studentC.nickname,
      ]);

      const groupText = uniqueMessage("group");
      await chatPage.sendText(groupText);

      const attachment = validImageAttachment("picture.png");
      const caption = uniqueMessage("withImage");
      await chatPage.attachImageAndSend(attachment, caption);
      await chatPage.expectMessageVisible(caption);
      // Вложение-изображение отображается и доступно для открытия (<img> с src).
      await chatPage.expectAttachmentVisible(attachment.name);

      // Участник группы тоже видит сообщения и вложение.
      const viewer = await openSecondUser(browser, api, studentB.nickname, studentB.password);
      try {
        const viewerChat = new ChatPage(viewer.page);
        await viewerChat.goto(groupId);
        await viewerChat.expectMessageVisible(groupText);
        await viewerChat.expectMessageVisible(caption);
        await viewerChat.expectAttachmentVisible(attachment.name);
      } finally {
        await viewer.context.close();
      }
    });
  });
});
