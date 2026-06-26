import { test } from "../fixtures/test";
import { loginAs } from "../helpers/session";
import { uniqueMessage } from "../helpers/unique";

test.describe("Сценарий 5: Ограничения удаления сообщений для студента", () => {
  test("Студент не может удалять чужие сообщения", async ({ page, api, users, chatPage }) => {
    // Данные готовим через API.
    const { user: studentA, tokens: tokensA } = await users.createWithTokens({ prefix: "delA" });
    const studentB = await users.student("delB");

    const personalMsg = uniqueMessage("personalA");
    const groupMsg = uniqueMessage("groupA");

    let personalChatId = "";
    let groupChatId = "";

    await test.step("Готовим личный и групповой чат с сообщениями от studentA", async () => {
      const personal = await api.createPersonalChat(tokensA.access_token, studentB.id);
      personalChatId = personal.id;
      await api.sendMessage(tokensA.access_token, personalChatId, personalMsg);

      const group = await api.createGroupChat(tokensA.access_token, "Чат удаления", [studentB.id]);
      groupChatId = group.id;
      await api.sendMessage(tokensA.access_token, groupChatId, groupMsg);
    });

    await test.step("Входим под studentB", async () => {
      await loginAs(page, api, studentB.nickname, studentB.password);
    });

    await test.step("Личный чат: studentB не может удалить сообщение studentA", async () => {
      await chatPage.goto(personalChatId);
      await chatPage.expectMessageVisible(personalMsg);
      await chatPage.expectCannotDelete(personalMsg);
    });

    await test.step("Групповой чат: studentB не может удалить сообщение studentA", async () => {
      await chatPage.goto(groupChatId);
      await chatPage.expectMessageVisible(groupMsg);
      await chatPage.expectCannotDelete(groupMsg);
    });

    await test.step("studentB может удалить собственное сообщение", async () => {
      const ownMsg = uniqueMessage("ownB");
      await chatPage.sendText(ownMsg);
      await chatPage.expectCanDelete(ownMsg);
      await chatPage.deleteOwnMessage(ownMsg);
      await chatPage.expectMessageAbsent(ownMsg);
    });
  });
});
