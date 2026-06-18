// Высокоуровневые обёртки эндпоинтов. Импортируйте отсюда:
//   import { authApi, chatsApi, messagesApi } from "./api/api";

import { getRefreshToken, request, setTokens } from "./client";
import type {
  AddParticipantRequest,
  Chat,
  CreateChatRequest,
  CreateMessageRequest,
  ListMessagesParams,
  LoginRequest,
  Message,
  Notification,
  ChangePasswordRequest,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  RegisterRequest,
  RoleUpgradeRequest,
  Session,
  TokenResponse,
  UpdateMessageRequest,
  UpdateUserRequest,
  User,
  UUID,
} from "./types";

export const authApi = {
  register(payload: RegisterRequest): Promise<User> {
    return request<User>("/auth/register", { method: "POST", body: payload, auth: false });
  },

  async login(payload: LoginRequest): Promise<TokenResponse> {
    const res = await request<TokenResponse>("/auth/login", {
      method: "POST",
      body: payload,
      auth: false,
    });
    setTokens(res);
    return res;
  },

  verifyEmail(token: string): Promise<User> {
    return request<User>("/auth/verify-email", {
      method: "POST",
      body: { token },
      auth: false,
    });
  },

  resendVerification(): Promise<{ detail: string }> {
    return request<{ detail: string }>("/auth/resend-verification", { method: "POST" });
  },

  forgotPassword(payload: ForgotPasswordRequest): Promise<{ detail: string }> {
    return request<{ detail: string }>("/auth/forgot-password", {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  resetPassword(payload: ResetPasswordRequest): Promise<void> {
    return request<void>("/auth/reset-password", {
      method: "POST",
      body: payload,
      auth: false,
    });
  },

  async logout(): Promise<void> {
    const refresh_token = getRefreshToken();
    try {
      await request<void>("/auth/logout", {
        method: "POST",
        body: { refresh_token },
        auth: false,
      });
    } catch {
      // отзыв на сервере не критичен для клиентского выхода
    } finally {
      setTokens(null);
    }
  },

  async logoutAll(): Promise<void> {
    try {
      await request<void>("/auth/logout-all", { method: "POST" });
    } finally {
      setTokens(null);
    }
  },
};

export const usersApi = {
  me(): Promise<User> {
    return request<User>("/users/me");
  },
  updateMe(payload: UpdateUserRequest): Promise<User> {
    return request<User>("/users/me", { method: "PATCH", body: payload });
  },
  changePassword(payload: ChangePasswordRequest): Promise<void> {
    return request<void>("/users/me/password", { method: "PATCH", body: payload });
  },
  getById(userId: UUID): Promise<User> {
    return request<User>(`/users/${userId}`);
  },
  search(query: string, limit = 10): Promise<User[]> {
    return request<User[]>("/users/search", {
      query: { q: query, limit },
    });
  },
  listSessions(): Promise<Session[]> {
    return request<Session[]>("/users/me/sessions");
  },
  revokeSession(sessionId: UUID): Promise<void> {
    return request<void>(`/users/me/sessions/${sessionId}`, { method: "DELETE" });
  },
  requestRoleUpgrade(reason?: string): Promise<RoleUpgradeRequest> {
    return request<RoleUpgradeRequest>("/users/me/role-upgrade-request", {
      method: "POST",
      body: { reason: reason || null },
    });
  },
  myRoleUpgradeRequests(): Promise<RoleUpgradeRequest[]> {
    return request<RoleUpgradeRequest[]>("/users/me/role-upgrade-requests");
  },
};

export const chatsApi = {
  getChats(): Promise<Chat[]> {
    return request<Chat[]>("/chats");
  },
  getChat(chatId: UUID): Promise<Chat> {
    return request<Chat>(`/chats/${chatId}`);
  },
  createChat(payload: CreateChatRequest): Promise<Chat> {
    return request<Chat>("/chats", { method: "POST", body: payload });
  },
  addParticipant(chatId: UUID, payload: AddParticipantRequest): Promise<Chat> {
    return request<Chat>(`/chats/${chatId}/participants`, { method: "POST", body: payload });
  },
  removeParticipant(chatId: UUID, userId: UUID): Promise<void> {
    return request<void>(`/chats/${chatId}/participants/${userId}`, { method: "DELETE" });
  },
  deleteChat(chatId: UUID): Promise<void> {
    return request<void>(`/chats/${chatId}`, { method: "DELETE" });
  },
};

export const messagesApi = {
  list(chatId: UUID, params: ListMessagesParams = {}): Promise<Message[]> {
    return request<Message[]>(`/chats/${chatId}/messages`, {
      query: params as Record<string, unknown>,
    });
  },
  send(chatId: UUID, payload: CreateMessageRequest): Promise<Message> {
    return request<Message>(`/chats/${chatId}/messages`, { method: "POST", body: payload });
  },
  edit(messageId: UUID, payload: UpdateMessageRequest): Promise<Message> {
    return request<Message>(`/messages/${messageId}`, { method: "PATCH", body: payload });
  },
  remove(messageId: UUID): Promise<void> {
    return request<void>(`/messages/${messageId}`, { method: "DELETE" });
  },
};

export const notificationsApi = {
  list(): Promise<Notification[]> {
    return request<Notification[]>("/notifications");
  },
  markRead(notificationId: UUID): Promise<Notification> {
    return request<Notification>(`/notifications/${notificationId}/read`, { method: "PATCH" });
  },
};
