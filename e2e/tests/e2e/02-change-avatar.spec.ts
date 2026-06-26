import { test, expect } from "../fixtures/test";
import { loginAs } from "../helpers/session";
import { validPng, invalidTextFile } from "../data/files";

test.describe("Сценарий 2: Смена аватарки", () => {
  test("Пользователь меняет аватарку", async ({ page, api, users, profilePage }) => {
    // Данные готовим через API: создаём подтверждённого пользователя и входим.
    const user = await users.create({ prefix: "ava" });
    const fullName = `${user.first_name} ${user.last_name}`;

    await test.step("Открываем профиль под пользователем", async () => {
      await loginAs(page, api, user.nickname, user.password);
      await profilePage.goto();
      // Изначально аватара нет — кнопка «Удалить» отсутствует.
      await profilePage.expectAvatarAbsent();
    });

    await test.step("Загрузка валидного изображения и отображение новой аватарки", async () => {
      await profilePage.uploadAvatar(validPng());
      await profilePage.expectAvatarPresent();
      await expect(profilePage.avatarImage(fullName)).toBeVisible();
    });

    await test.step("Аватарка сохраняется после перезагрузки страницы", async () => {
      await page.reload();
      await expect(page.getByRole("heading", { name: "Аватар" })).toBeVisible();
      await profilePage.expectAvatarPresent();
      await expect(profilePage.avatarImage(fullName)).toBeVisible();
    });

    await test.step("Невалидный формат отклоняется сервером", async () => {
      await profilePage.uploadAvatar(invalidTextFile());
      await expect(profilePage.avatarError("Недопустимый тип файла")).toBeVisible();
    });
  });
});
