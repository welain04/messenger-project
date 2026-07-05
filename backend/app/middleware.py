"""Простой middleware для извлечения текущего пользователя из JWT в request.state."""

from __future__ import annotations

import sentry_sdk
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .config import get_settings
from .deps import _user_from_payload
from .security import decode_access_token


class JWTUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.user = None
        request.state.sid = None
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
            payload = decode_access_token(token)
            if payload:
                request.state.user = _user_from_payload(payload)
                request.state.sid = payload.get("sid")
        if get_settings().SENTRY_DSN.strip():
            user = request.state.user
            sentry_sdk.set_user({"id": str(user.id)} if user else None)
        return await call_next(request)
