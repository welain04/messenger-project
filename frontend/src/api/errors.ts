import { ApiError } from "./client";

/** Преобразует ошибку API в понятное русское сообщение для UI. */
export function formatApiError(
  error: unknown,
  fallback = "Не удалось выполнить запрос"
): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === "string") {
      return error.detail;
    }

    if (Array.isArray(error.detail)) {
      const messages = error.detail
        .map((item) => {
          if (!item || typeof item !== "object") return null;
          const msg = (item as { msg?: string }).msg;
          if (typeof msg === "string" && msg.startsWith("Value error, ")) {
            return msg.slice("Value error, ".length);
          }
          return typeof msg === "string" ? msg : null;
        })
        .filter(Boolean) as string[];

      if (messages.length > 0) {
        return messages.join("; ");
      }
    }

    if (error.status === 401 || error.status === 403) {
      return "Войдите в систему или проверьте права доступа";
    }

    return error.message || fallback;
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
