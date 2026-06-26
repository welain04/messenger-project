/**
 * Тонкая обёртка над REST API бэкенда для подготовки данных в тестах.
 *
 * Принцип: данные готовим через API (быстро и стабильно), а UI используем
 * только для проверки пользовательского сценария.
 */

import { APIRequestContext, expect, request as pwRequest } from "@playwright/test";
import { API_BASE_URL, DEFAULT_PASSWORD } from "./config";

export type Role = "student" | "curator" | "admin";

export interface TestUser {
  id: string;
  nickname: string;
  email: string;
  role: Role;
  first_name: string;
  last_name: string;
  password: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface OutboxEntry {
  to: string;
  subject: string;
  token: string;
  link: string;
}

export interface Chat {
  id: string;
  type: "personal" | "group";
  title: string | null;
  participant_ids: string[];
  created_by: string;
}

export interface Message {
  id: string;
  chat_id: string;
  author_id: string;
  text: string;
}

const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

export class BackendApi {
  constructor(private readonly ctx: APIRequestContext) {}

  static async create(): Promise<BackendApi> {
    // НЕ используем baseURL: при пути с ведущим "/" префикс /api/v1 теряется
    // (URL-резолвинг). Поэтому строим абсолютные URL через `u()`.
    const ctx = await pwRequest.newContext();
    return new BackendApi(ctx);
  }

  /** Абсолютный URL эндпоинта (надёжно сохраняет префикс /api/v1). */
  private u(path: string): string {
    return `${API_BASE_URL}${path}`;
  }

  async dispose(): Promise<void> {
    await this.ctx.dispose();
  }

  get context(): APIRequestContext {
    return this.ctx;
  }

  /** Создаёт пользователя напрямую (verified) через тестовый эндпоинт. */
  async createUser(opts: {
    nickname: string;
    password?: string;
    email?: string;
    role?: Role;
    first_name?: string;
    last_name?: string;
    email_verified?: boolean;
  }): Promise<TestUser> {
    const password = opts.password ?? DEFAULT_PASSWORD;
    const res = await this.ctx.post(this.u("/_test/users"), {
      data: {
        nickname: opts.nickname,
        password,
        email: opts.email,
        role: opts.role ?? "student",
        first_name: opts.first_name ?? "Test",
        last_name: opts.last_name ?? "User",
        email_verified: opts.email_verified ?? true,
      },
    });
    expect(res.ok(), `createUser failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    const body = await res.json();
    return { ...body, password } as TestUser;
  }

  async login(nickname: string, password: string): Promise<TokenPair> {
    const res = await this.ctx.post(this.u("/auth/login"), { data: { nickname, password } });
    expect(res.ok(), `login failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as TokenPair;
  }

  /** Создаёт пользователя и сразу возвращает его токены. */
  async createUserWithTokens(opts: Parameters<BackendApi["createUser"]>[0]): Promise<{
    user: TestUser;
    tokens: TokenPair;
  }> {
    const user = await this.createUser(opts);
    const tokens = await this.login(user.nickname, user.password);
    return { user, tokens };
  }

  async register(payload: {
    nickname: string;
    password: string;
    email: string;
    first_name: string;
    last_name: string;
  }) {
    const res = await this.ctx.post(this.u("/auth/register"), { data: payload });
    return res;
  }

  async forgotPassword(email: string): Promise<void> {
    const res = await this.ctx.post(this.u("/auth/forgot-password"), { data: { email } });
    expect(res.ok(), `forgotPassword failed: ${res.status()}`).toBeTruthy();
  }

  /** Последнее письмо для адреса (verification/reset token). */
  async lastEmail(email: string): Promise<OutboxEntry> {
    const res = await this.ctx.get(this.u("/_test/emails/last"), { params: { email } });
    expect(res.ok(), `lastEmail failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as OutboxEntry;
  }

  async createPersonalChat(token: string, otherUserId: string): Promise<Chat> {
    const res = await this.ctx.post(this.u("/chats"), {
      headers: auth(token),
      data: { type: "personal", participant_ids: [otherUserId] },
    });
    expect(res.ok(), `createPersonalChat failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as Chat;
  }

  async createGroupChat(token: string, title: string, participantIds: string[]): Promise<Chat> {
    const res = await this.ctx.post(this.u("/chats"), {
      headers: auth(token),
      data: { type: "group", title, participant_ids: participantIds },
    });
    expect(res.ok(), `createGroupChat failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as Chat;
  }

  async addParticipant(token: string, chatId: string, userId: string): Promise<Chat> {
    const res = await this.ctx.post(this.u(`/chats/${chatId}/participants`), {
      headers: auth(token),
      data: { user_id: userId },
    });
    expect(res.ok(), `addParticipant failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as Chat;
  }

  async sendMessage(token: string, chatId: string, text: string): Promise<Message> {
    const res = await this.ctx.post(this.u(`/chats/${chatId}/messages`), {
      headers: auth(token),
      data: { text },
    });
    expect(res.ok(), `sendMessage failed: ${res.status()} ${await res.text()}`).toBeTruthy();
    return (await res.json()) as Message;
  }

  async listMessages(token: string, chatId: string): Promise<Message[]> {
    const res = await this.ctx.get(this.u(`/chats/${chatId}/messages`), { headers: auth(token) });
    expect(res.ok(), `listMessages failed: ${res.status()}`).toBeTruthy();
    return (await res.json()) as Message[];
  }
}
