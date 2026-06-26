/**
 * Кастомные фикстуры Playwright.
 *
 * - `api`     — обёртка над REST API бэкенда (подготовка данных).
 * - `users`   — фабрика пользователей (student/curator/admin) с уникальными
 *               никнеймами и подтверждённым email.
 * - POM-фикстуры (`authPage`, `chatsPage`, `chatPage`, `profilePage`).
 */

import { test as base, expect } from "@playwright/test";
import { BackendApi, Role, TestUser, TokenPair } from "../helpers/backend";
import { uniqueNickname } from "../helpers/unique";
import { AuthPage } from "../pom/AuthPage";
import { ChatsPage } from "../pom/ChatsPage";
import { ChatPage } from "../pom/ChatPage";
import { ProfilePage } from "../pom/ProfilePage";

export interface UserFactory {
  create(opts?: {
    prefix?: string;
    role?: Role;
    password?: string;
    email_verified?: boolean;
  }): Promise<TestUser>;
  createWithTokens(opts?: {
    prefix?: string;
    role?: Role;
  }): Promise<{ user: TestUser; tokens: TokenPair }>;
  student(prefix?: string): Promise<TestUser>;
  curator(prefix?: string): Promise<TestUser>;
}

type Fixtures = {
  api: BackendApi;
  users: UserFactory;
  authPage: AuthPage;
  chatsPage: ChatsPage;
  chatPage: ChatPage;
  profilePage: ProfilePage;
};

export const test = base.extend<Fixtures>({
  api: async ({}, use) => {
    const api = await BackendApi.create();
    await use(api);
    await api.dispose();
  },

  users: async ({ api }, use) => {
    const factory: UserFactory = {
      create: (opts = {}) =>
        api.createUser({
          nickname: uniqueNickname(opts.prefix ?? "user"),
          role: opts.role ?? "student",
          password: opts.password,
          email_verified: opts.email_verified ?? true,
        }),
      createWithTokens: (opts = {}) =>
        api.createUserWithTokens({
          nickname: uniqueNickname(opts.prefix ?? "user"),
          role: opts.role ?? "student",
        }),
      student: (prefix = "stud") =>
        api.createUser({ nickname: uniqueNickname(prefix), role: "student" }),
      curator: (prefix = "cur") =>
        api.createUser({ nickname: uniqueNickname(prefix), role: "curator" }),
    };
    await use(factory);
  },

  authPage: async ({ page }, use) => {
    await use(new AuthPage(page));
  },
  chatsPage: async ({ page }, use) => {
    await use(new ChatsPage(page));
  },
  chatPage: async ({ page }, use) => {
    await use(new ChatPage(page));
  },
  profilePage: async ({ page }, use) => {
    await use(new ProfilePage(page));
  },
});

export { expect };
