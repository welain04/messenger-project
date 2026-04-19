// Авто-составленные типы под бэкенд `online-school-messenger`.
// Соответствуют openapi.json (backend/openapi.json).

export type UUID = string;
export type ISODateTime = string;

export type UserRole = "student" | "curator";
export type ChatType = "personal" | "group";

export interface User {
  id: UUID;
  nickname: string;
  role: UserRole;
  created_at: ISODateTime;
}

export interface MessagePreview {
  id: UUID;
  author_id: UUID;
  text: string;
  sent_at: ISODateTime;
}

export interface Chat {
  id: UUID;
  type: ChatType;
  title: string | null;
  participant_ids: UUID[];
  created_by: UUID;
  created_at: ISODateTime;
  last_message: MessagePreview | null;
  unread_count: number;
}

export interface Message {
  id: UUID;
  chat_id: UUID;
  author_id: UUID;
  text: string;
  sent_at: ISODateTime;
  is_read: boolean;
  edited_at: ISODateTime | null;
}

export interface Notification {
  id: UUID;
  user_id: UUID;
  message: string;
  is_read: boolean;
  created_at: ISODateTime;
}

// ---- Запросы ----

export interface RegisterRequest {
  nickname: string;
  password: string;
  role: UserRole;
}

export interface LoginRequest {
  nickname: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
}

export interface UpdateUserRequest {
  nickname: string;
}

export interface CreateChatRequest {
  type: ChatType;
  title?: string | null;
  participant_ids: UUID[];
}

export interface AddParticipantRequest {
  user_id: UUID;
}

export interface CreateMessageRequest {
  text: string;
}

export interface UpdateMessageRequest {
  text: string;
}

export interface ListMessagesParams {
  limit?: number;
  offset?: number;
}
