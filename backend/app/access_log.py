"""Access log middleware: POST / PATCH / DELETE."""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .rate_limit import _client_ip
from .structured_log import log_http_request

_MUTATING_METHODS = frozenset({"POST", "PATCH", "DELETE"})
_SKIP_PATHS = frozenset({"/health", "/health/sentry-test"})


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in _MUTATING_METHODS or request.url.path in _SKIP_PATHS:
            return await call_next(request)

        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status = 500

        try:
            response = await call_next(request)
            status = response.status_code
            response.headers.setdefault("X-Request-ID", request_id)
            return response
        finally:
            user = getattr(request.state, "user", None)
            duration_ms = (time.perf_counter() - started) * 1000
            log_http_request(
                method=request.method,
                path=request.url.path,
                status=status,
                duration_ms=duration_ms,
                user_id=user.id if user else None,
                client_ip=_client_ip(request),
                request_id=request_id,
            )
