import { test, expect } from "../fixtures/test";
import { DEFAULT_PASSWORD } from "../helpers/config";
import { uniqueNickname, uniqueEmail } from "../helpers/unique";

test.describe("Сценарий 1: Регистрация, подтверждение почты и валидация форм", () => {
  test("Пользователь регистрируется, подтверждает почту и попадает на главную страницу", async ({
    page,
    api,
    authPage,
  }) => {
    const nickname = uniqueNickname("reg");
    const email = `${nickname}@example.com`;

    await test.step("Успешная регистрация нового пользователя", async () => {
      await authPage.goto();
      await authPage.openRegister();
      await authPage.fillRegister({
        nickname,
        firstName: "Иван",
        lastName: "Петров",
        email,
        password: DEFAULT_PASSWORD,
      });
      await authPage.registerSubmit.click();
      // После регистрации происходит автоматический вход и переход к чатам.
      await page.waitForURL("**/chats");
      await expect(page.getByText("Подтвердите email", { exact: false })).toBeVisible();
    });

    await test.step("Подтверждение email по ссылке из письма", async () => {
      const { token } = await api.lastEmail(email);
      await page.goto(`/verify-email?token=${token}`);
      await expect(page.getByText("Email подтверждён", { exact: false })).toBeVisible();
    });

    await test.step("Переход на главную страницу после подтверждения", async () => {
      await page.getByRole("link", { name: "Перейти к чатам" }).click();
      await page.waitForURL("**/chats");
      // Баннер о подтверждении email больше не показывается.
      await expect(page.getByText("Подтвердите email", { exact: false })).toHaveCount(0);
    });

    await test.step("Отображение данных пользователя", async () => {
      await expect(page.getByText(nickname, { exact: true })).toBeVisible();
      await page.goto("/profile");
      await expect(page.getByText(email)).toBeVisible();
      await expect(page.getByText("(подтверждён)")).toBeVisible();
    });
  });

  test("Валидация формы регистрации", async ({ page, api, authPage }) => {
    // Существующий пользователь — для проверки дублирования email/nickname.
    const existing = await api.createUser({
      nickname: uniqueNickname("dup"),
      email: `${uniqueNickname("dupmail")}@example.com`,
    });

    await authPage.goto();
    await authPage.openRegister();

    const validBase = {
      nickname: uniqueNickname("ok"),
      firstName: "Анна",
      lastName: "Смирнова",
      email: uniqueEmail("ok"),
      password: DEFAULT_PASSWORD,
    };

    await test.step("Пустой nickname отклоняется", async () => {
      await authPage.fillRegister({ ...validBase, nickname: "" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.nickname);
      expect(page.url()).toContain("/auth");
    });

    await test.step("Слишком короткий nickname отклоняется", async () => {
      await authPage.fillRegister({ ...validBase, nickname: "ab" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.nickname);
    });

    await test.step("Слишком длинный nickname ограничивается (maxlength=30)", async () => {
      await expect(authPage.nickname).toHaveAttribute("maxlength", "30");
      await authPage.nickname.fill("a".repeat(35));
      expect((await authPage.nickname.inputValue()).length).toBe(30);
    });

    await test.step("Недопустимые символы в nickname отклоняются", async () => {
      await authPage.fillRegister({ ...validBase, nickname: "bad nick$" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.nickname);
    });

    await test.step("Пустой email отклоняется", async () => {
      await authPage.fillRegister({ ...validBase, email: "" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.email);
    });

    await test.step("Некорректный email отклоняется", async () => {
      await authPage.fillRegister({ ...validBase, email: "not-an-email" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.email);
    });

    await test.step("Пустой пароль отклоняется", async () => {
      await authPage.fillRegister({ ...validBase, password: "" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.password);
    });

    await test.step("Слишком короткий пароль отклоняется", async () => {
      await authPage.fillRegister({ ...validBase, password: "123" });
      await authPage.registerSubmit.click();
      await authPage.expectFieldInvalid(authPage.password);
    });

    await test.step("Дублирование email отклоняется сервером", async () => {
      await authPage.fillRegister({
        ...validBase,
        nickname: uniqueNickname("ok"),
        email: existing.email,
      });
      await authPage.registerSubmit.click();
      await expect(authPage.errorMessage("Этот email уже зарегистрирован")).toBeVisible();
    });

    await test.step("Дублирование nickname отклоняется сервером", async () => {
      await authPage.fillRegister({
        ...validBase,
        nickname: existing.nickname,
        email: uniqueEmail("ok"),
      });
      await authPage.registerSubmit.click();
      await expect(authPage.errorMessage("Этот никнейм уже занят")).toBeVisible();
    });

    // Примечание: на форме регистрации нет поля подтверждения пароля,
    // поэтому проверка несовпадения паролей выполняется в сценариях 3 и 4.
  });

  test("Валидация формы входа", async ({ page, api, authPage }) => {
    const user = await api.createUser({ nickname: uniqueNickname("login") });

    await authPage.goto();
    await authPage.openLogin();

    await test.step("Пустой логин отклоняется", async () => {
      await authPage.fillLogin({ nickname: "", password: DEFAULT_PASSWORD });
      await authPage.loginSubmit.click();
      await authPage.expectFieldInvalid(authPage.nickname);
      expect(page.url()).toContain("/auth");
    });

    await test.step("Пустой пароль отклоняется", async () => {
      await authPage.fillLogin({ nickname: user.nickname, password: "" });
      await authPage.loginSubmit.click();
      await authPage.expectFieldInvalid(authPage.password);
    });

    await test.step("Неверный пароль отклоняется", async () => {
      await authPage.fillLogin({ nickname: user.nickname, password: "WrongPassword123" });
      await authPage.loginSubmit.click();
      await expect(authPage.errorMessage("Неверный никнейм или пароль")).toBeVisible();
    });

    await test.step("Несуществующий пользователь отклоняется", async () => {
      await authPage.fillLogin({ nickname: uniqueNickname("ghost"), password: DEFAULT_PASSWORD });
      await authPage.loginSubmit.click();
      await expect(authPage.errorMessage("Неверный никнейм или пароль")).toBeVisible();
    });

    await test.step("Корректный вход выполняется успешно", async () => {
      await authPage.fillLogin({ nickname: user.nickname, password: user.password });
      await authPage.loginSubmit.click();
      await page.waitForURL("**/chats");
      await expect(page.getByText(user.nickname, { exact: true })).toBeVisible();
    });
  });
});
