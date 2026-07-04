/** Синхронизировано с backend/app/password_policy.py */

export const MIN_PASSWORD_LENGTH = 8;

/** HTML5: минимум 8 символов, хотя бы одна буква и одна цифра. */
export const PASSWORD_PATTERN = "(?=.*[A-Za-z])(?=.*\\d).{8,}";

export const PASSWORD_HINT = "минимум 8 символов, буква и цифра";

export const PASSWORD_TITLE =
  "Минимум 8 символов, хотя бы одна буква (A–Z, a–z) и одна цифра";
