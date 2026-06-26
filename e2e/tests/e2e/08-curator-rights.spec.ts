import { test } from "../fixtures/test";
import { loginAs } from "../helpers/session";
import { uniqueMessage } from "../helpers/unique";

test.describe("Сценарий 8: Права куратора", () => {
  test("Куратор управляет групповым чатом", async ({ page, api, users, chatsPage, chatPage }) => {
    const curator = await users.curator("cur8");
    const { user: studentA, tokens: tokensA } = await users.createWithTokens({ prefix: "cur8A" });
    const studentB = await users.student("cur8B");
    const studentC = await users.student("cur8C");

    let groupId = "";

    await test.step("Куратор входит и создаёт групповой чат", async () => {
      await loginAs(page, api, curator.nickname, curator.password);
      await chatsPage.goto();
      groupId = await chatsPage.createGroupChat("Кураторская группа", [
        studentA.nickname,
        studentB.nickname,
      ]);
    });

    await test.step("Куратор добавляет участника, удаляет и снова добавляет", async () => {
      await chatPage.openMembers();
      await chatPage.addMember(studentC.nickname);
      await chatPage.expectMemberPresent(studentC.nickname);

      await chatPage.removeMember(studentB.nickname);
      await chatPage.expectMemberAbsent(studentB.nickname);

      await chatPage.addMember(studentB.nickname);
      await chatPage.expectMemberPresent(studentB.nickname);
    });

    await test.step("Куратор удаляет сообщение другого участника в группе", async () => {
      const aMessage = uniqueMessage("studentAgroup");
      await api.sendMessage(tokensA.access_token, groupId, aMessage);

      await chatPage.goto(groupId);
      await chatPage.expectMessageVisible(aMessage);
      await chatPage.expectCanDelete(aMessage);
      await chatPage.deleteMessage(aMessage);
      await chatPage.expectMessageAbsent(aMessage);
    });

    await test.step("Куратор может удалить собственное сообщение", async () => {
      const ownMessage = uniqueMessage("curatorOwn");
      await chatPage.sendText(ownMessage);
      await chatPage.expectCanDelete(ownMessage);
      await chatPage.deleteOwnMessage(ownMessage);
      await chatPage.expectMessageAbsent(ownMessage);
    });

    await test.step("В личном чате куратор НЕ может удалить чужое сообщение", async () => {
      const personal = await api.createPersonalChat(tokensA.access_token, curator.id);
      const personalMessage = uniqueMessage("studentApersonal");
      await api.sendMessage(tokensA.access_token, personal.id, personalMessage);

      await chatPage.goto(personal.id);
      await chatPage.expectMessageVisible(personalMessage);
      await chatPage.expectCannotDelete(personalMessage);
    });
  });
});
