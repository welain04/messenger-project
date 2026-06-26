/**
 * Генерация уникальных идентификаторов для независимости тестов.
 *
 * Тесты делят одну тестовую БД в рамках прогона, поэтому никнеймы/email должны
 * быть уникальными между тестами и запусками. Никнейм обязан соответствовать
 * NICKNAME_RE на бэкенде: ^[A-Za-z0-9_]+$, длина 3..30.
 */

let counter = 0;

const randomChunk = (): string => Math.random().toString(36).slice(2, 7);

/**
 * Уникальный никнейм с читаемым префиксом, гарантированно <= 30 символов и
 * только из разрешённых символов [A-Za-z0-9_].
 */
export function uniqueNickname(prefix = "u"): string {
  counter += 1;
  const safePrefix = prefix.replace(/[^A-Za-z0-9]/g, "").slice(0, 10) || "u";
  const base = `${safePrefix}_${Date.now().toString(36)}${randomChunk()}${counter}`;
  return base.slice(0, 30);
}

/** Email на основе уникального никнейма. */
export function uniqueEmail(prefix = "user"): string {
  return `${uniqueNickname(prefix)}@example.com`;
}

/** Уникальный текст сообщения (чтобы надёжно искать его в DOM). */
export function uniqueMessage(label = "msg"): string {
  counter += 1;
  return `${label}-${Date.now().toString(36)}-${randomChunk()}-${counter}`;
}
