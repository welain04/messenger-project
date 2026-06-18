// Авто-составленные типы под бэкенд `online-school-messenger`.
// Соответствуют openapi.json (backend/openapi.json).

export type UUID = string;
export type ISODateTime = string;

export type UserRole = "student" | "curator" | "admin";
export type ChatType = "personal" | "group";

export interface User {
  id: UUID;
  nickname: string;
  role: UserRole;
  first_name: string;
  last_name: string;
  created_at: ISODateTime;
  // Приватные поля (приходят только в /users/me и ответах auth).
  email?: string;
  email_verified?: boolean;
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
  email: string;
  first_name: string;
  last_name: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface LoginRequest {
  nickname: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface Session {
  id: UUID;
  user_agent: string | null;
  ip: string | null;
  created_at: ISODateTime;
  last_seen_at: ISODateTime;
  current: boolean;
}

export type RoleUpgradeStatus = "pending" | "approved" | "rejected";

export interface RoleUpgradeRequest {
  id: UUID;
  user_id: UUID;
  requested_role: UserRole;
  status: RoleUpgradeStatus;
  reason: string | null;
  reviewed_by: UUID | null;
  review_note: string | null;
  created_at: ISODateTime;
  reviewed_at: ISODateTime | null;
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
