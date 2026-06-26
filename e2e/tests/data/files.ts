/**
 * Бинарные фикстуры для загрузки файлов (аватары/вложения).
 *
 * Используем in-memory буферы (Playwright `setInputFiles({ buffer })`), чтобы не
 * хранить бинарные файлы в репозитории и полностью контролировать mime-type.
 */

export interface InMemoryFile {
  name: string;
  mimeType: string;
  buffer: Buffer;
}

// Валидный 1x1 PNG (прозрачный пиксель).
const PNG_1x1_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

export const validPng = (name = "avatar.png"): InMemoryFile => ({
  name,
  mimeType: "image/png",
  buffer: Buffer.from(PNG_1x1_BASE64, "base64"),
});

export const validImageAttachment = (name = "attachment.png"): InMemoryFile => ({
  name,
  mimeType: "image/png",
  buffer: Buffer.from(PNG_1x1_BASE64, "base64"),
});

// Невалидный для аватара формат (text/plain отсутствует в ALLOWED_AVATAR_MIMES).
export const invalidTextFile = (name = "not-an-image.txt"): InMemoryFile => ({
  name,
  mimeType: "text/plain",
  buffer: Buffer.from("Это не картинка, а обычный текстовый файл.", "utf-8"),
});
