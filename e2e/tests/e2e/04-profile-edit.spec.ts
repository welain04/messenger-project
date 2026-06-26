import { test, expect } from "../fixtures/test";
import { loginAs } from "../helpers/session";
import { uniqueNickname } from "../helpers/unique";
import { DEFAULT_PASSWORD } from "../helpers/config";

test.describe("Сценарий 4: Изменение профиля", () => {
  test("Пользователь меняет никнейм и пароль", async ({ page, api, users, authPage, profilePage }) => {
    const user = await users.create({ prefix: "prof" });
    const newNickname = uniqueNickname("prof2");
    const oldPassword = DEFAULT_PASSWORD;
    const newPassword = "Changed789";

    await test.step("Открываем профиль под пользователем", async () => {
      await loginAs(page, api, user.nickname, user.password);
      await profilePage.goto();
    });

    await test.step("Изменение nickname и отображение нового значения", async () => {
      await profilePage.changeNickname(newNickname);
      // Шапка приложения показывает «Вы: {nickname}» — должен обновиться.
      await expect(page.getByText(newNickname, { exact: true })).toBeVisible();
      await expect(page.getByText(`@${newNickname}`)).toBeVisible();
    });

    await test.step("Изменение пароля завершает сессию (редирект на вход)", async () => {
      await profilePage.changePassword(oldPassword, newPassword);
      await page.waitForURL("**/auth");
    });

    await test.step("Повторный вход с новым никнеймом и новым паролем", async () => {
      await authPage.login(newNickname, newPassword);
      await expect(page.getByText(newNickname, { exact: true })).toBeVisible();
    });

    await test.step("Вход со старым паролем невозможен", async () => {
      await page.goto("/auth");
      await authPage.loginExpectingError(newNickname, oldPassword);
      await expect(authPage.errorMessage("Неверный никнейм или пароль")).toBeVisible();
    });
  });
});
