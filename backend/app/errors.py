"""Русские сообщения об ошибках валидации и API."""

from __future__ import annotations

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

# Человекочитаемые имена полей в формах API
_FIELD_NAMES: dict[str, str] = {
    "nickname": "Никнейм",
    "password": "Пароль",
    "role": "Роль",
    "text": "Текст сообщения",
    "title": "Название чата",
    "participant_ids": "Участники",
    "type": "Тип чата",
    "user_id": "Пользователь",
}


def _field_label(loc: tuple[str | int, ...]) -> str:
    for part in reversed(loc):
        if isinstance(part, str) and part not in ("body", "query"):
            return _FIELD_NAMES.get(part, part)
    return "Поле"


def _translate_validation_item(err: dict) -> str:
    err_type = err.get("type", "")
    loc = tuple(err.get("loc", ()))
    field = _field_label(loc)
    ctx = err.get("ctx") or {}
    msg = str(err.get("msg", ""))

    # Кастомные ValueError из Pydantic model_validator / field_validator
    if err_type == "value_error":
        if msg.startswith("Value error, "):
            return msg.removeprefix("Value error, ")
        return msg

    if err_type == "missing":
        return f"{field}: обязательное поле"

    if err_type == "string_too_short":
        min_len = ctx.get("min_length", "")
        return f"{field}: минимум {min_len} символов"

    if err_type == "string_too_long":
        max_len = ctx.get("max_length", "")
        return f"{field}: максимум {max_len} символов"

    if err_type in ("uuid_parsing", "uuid_type"):
        return f"{field}: некорректный идентификатор"

    if err_type == "string_pattern_mismatch":
        if "nickname" in loc:
            return f"{field}: только латинские буквы, цифры и символ _"
        return f"{field}: недопустимый формат"

    if err_type == "list_too_short":
        min_len = ctx.get("min_length", "")
        return f"{field}: укажите не менее {min_len} элементов"

    if err_type == "enum":
        return f"{field}: недопустимое значение"

    # Fallback — оригинальное сообщение Pydantic (на случай новых типов)
    return msg or "Проверьте введённые данные"


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Возвращает ошибки валидации в виде одной русской строки."""
    messages = [_translate_validation_item(err) for err in exc.errors()]
    detail = messages[0] if len(messages) == 1 else "; ".join(messages)
    return JSONResponse(status_code=422, content={"detail": detail})
