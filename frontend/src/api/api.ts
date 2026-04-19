// Высокоуровневые обёртки эндпоинтов. Импортируйте отсюда:
//   import { authApi, chatsApi, messagesApi } from "./api/api";

import { request, setToken } from "./client";
import type {
  AddParticipantRequest,
  Chat,
  CreateChatRequest,
  CreateMessageRequest,
  ListMessagesParams,
  LoginRequest,
  Message,
  Notification,
  RegisterRequest,
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
    setToken(res.access_token);
    return res;
  },

  logout(): void {
    setToken(null);
  },
};

export const usersApi = {
  me(): Promise<User> {
    return request<User>("/users/me");
  },
  updateMe(payload: UpdateUserRequest): Promise<User> {
    return request<User>("/users/me", { method: "PATCH", body: payload });
  },
  getById(userId: UUID): Promise<User> {
    return request<User>(`/users/${userId}`);
  },
  search(query: string, limit = 10): Promise<User[]> {
    return request<User[]>("/users/search", {
      query: { q: query, limit },
    });
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
