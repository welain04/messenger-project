import { test, expect } from "../fixtures/test";
import { uniqueNickname } from "../helpers/unique";
import { DEFAULT_PASSWORD } from "../helpers/config";
import { ForgotPasswordPage, ResetPasswordPage } from "../pom/PasswordRecoveryPages";

test.describe("Сценарий 3: Восстановление пароля", () => {
  test("Пользователь восстанавливает пароль через почту", async ({ page, api, authPage }) => {
    const nickname = uniqueNickname("reset");
    const email = `${nickname}@example.com`;
    const oldPassword = DEFAULT_PASSWORD;
    const newPassword = "NewPass456";

    // Подготовка данных через API: пользователь с известными email и паролем.
    await api.createUser({ nickname, email, password: oldPassword });

    const forgot = new ForgotPasswordPage(page);
    const reset = new ResetPasswordPage(page);

    await test.step("Отправка запроса на восстановление", async () => {
      await forgot.goto();
      await forgot.requestReset(email);
      // Сервер всегда отвечает успехом (без раскрытия наличия аккаунта).
      await expect(page.getByText(/Если аккаунт существует/i)).toBeVisible();
    });

    let token = "";
    await test.step("Получение reset token из письма", async () => {
      const mail = await api.lastEmail(email);
      token = mail.token;
      expect(token.length).toBeGreaterThan(0);
    });

    await test.step("Установка нового пароля по токену", async () => {
      await reset.goto(token);
      await reset.setNewPassword(newPassword);
      await expect(page.getByText("Пароль изменён")).toBeVisible();
      await page.getByRole("button", { name: "Перейти ко входу" }).click();
      await page.waitForURL("**/auth");
    });

    await test.step("Успешный вход с новым паролем", async () => {
      await authPage.login(nickname, newPassword);
      await expect(page.getByText(nickname, { exact: true })).toBeVisible();
    });

    await test.step("Вход со старым паролем невозможен", async () => {
      await page.goto("/auth");
      await authPage.loginExpectingError(nickname, oldPassword);
      await expect(authPage.errorMessage("Неверный никнейм или пароль")).toBeVisible();
    });
  });
});
