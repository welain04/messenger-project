"""Проверка structured logging (п. 4–6): JSON, access, business, error, sanitize."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["APP_ENV"] = "development"
os.environ["LOG_JSON"] = "true"
os.environ["SMTP_HOST"] = ""
os.environ.setdefault("DATABASE_PATH", str(ROOT / ".verify_logging.db"))
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_REGISTER_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_VERIFY_PER_MIN", "0")
os.environ.setdefault("ENABLE_TEST_ENDPOINTS", "true")

from fastapi.testclient import TestClient  # noqa: E402

from app import db, mailer, storage  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.logging_config import setup_logging  # noqa: E402
from app.main import app  # noqa: E402


class _JsonCaptureHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[dict] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.records.append(json.loads(record.getMessage()))
        except json.JSONDecodeError:
            pass


def _attach_capture() -> _JsonCaptureHandler:
    setup_logging(get_settings())
    handler = _JsonCaptureHandler()
    handler.setLevel(logging.DEBUG)
    for name in ("messenger", "messenger.access", "messenger.business", "messenger.error"):
        log = logging.getLogger(name)
        log.handlers.clear()
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)
        log.propagate = False
    return handler


def _events(capture: _JsonCaptureHandler, event: str) -> list[dict]:
    return [r for r in capture.records if r.get("event") == event]


def _assert_no_secrets(text: str) -> None:
    forbidden = ("Secret123", "SuperPassword", "hashed_password")
    for token in forbidden:
        if token in text:
            raise AssertionError(f"Секрет попал в лог: {token!r}")


def main() -> None:
    db.init_db()
    storage.reset_storage()
    mailer.outbox.clear()
    capture = _attach_capture()
    c = TestClient(app)

    r = c.post(
        "/api/v1/auth/register",
        json={
            "nickname": "loguser",
            "password": "Secret123",
            "email": "loguser@example.com",
            "first_name": "Log",
            "last_name": "User",
        },
    )
    assert r.status_code == 201, r.text

    business = _events(capture, "business")
    register_events = [e for e in business if e.get("action") == "auth.register"]
    assert register_events, "Нет business-события auth.register"
    reg = register_events[-1]
    assert reg["entity_type"] == "user"
    assert reg["data"]["nickname"] == "loguser"
    assert "@" in reg["data"]["email"] and "Secret" not in reg["data"]["email"]

    token = mailer.outbox[-1]["token"]
    r = c.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200, r.text

    r = c.post("/api/v1/auth/login", json={"nickname": "loguser", "password": "Secret123"})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = c.post(
        "/api/v1/_test/users",
        json={"nickname": "logbuddy", "role": "student", "email_verified": True},
    )
    assert r.status_code == 201, r.text
    buddy_id = r.json()["id"]

    r = c.post(
        "/api/v1/chats",
        headers=headers,
        json={"type": "personal", "participant_ids": [buddy_id]},
    )
    assert r.status_code == 201, r.text

    chat_events = [e for e in _events(capture, "business") if e.get("action") == "chat.created"]
    assert chat_events, "Нет business-события chat.created"
    chat_ev = chat_events[-1]
    assert chat_ev["entity_type"] == "chat"
    assert chat_ev["data"]["type"] == "personal"

    access = _events(capture, "http_request")
    assert access, "Нет access-log (http_request)"
    sample = access[-1]
    for key in ("method", "path", "status", "duration_ms"):
        assert key in sample, f"В access-log нет поля {key}"
    assert sample["method"] in {"POST", "PATCH", "DELETE"}

    r = c.get("/health/sentry-test", params={"key": "wrong-key"})
    assert r.status_code == 404

    from app.exception_handlers import unhandled_exception_handler  # noqa: E402
    from starlette.requests import Request  # noqa: E402

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/_verify/crash",
        "headers": [],
        "query_string": b"",
    }

    async def _receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, _receive)
    import asyncio

    asyncio.run(
        unhandled_exception_handler(request, RuntimeError("verify logging crash"))
    )

    errors = _events(capture, "error")
    assert errors, "Нет error-события"
    err = errors[-1]
    assert err["exc_type"] == "RuntimeError"
    assert "verify logging crash" in err["error_message"]
    assert "RuntimeError" in err["stack"]

    dump = json.dumps(capture.records, ensure_ascii=False)
    _assert_no_secrets(dump)

    print(f"OK: {len(capture.records)} JSON-записей, проверки пройдены")
    print(f"  business auth.register: {reg['message']}")
    print(f"  business chat.created:  {chat_ev['message']}")
    print(f"  access:                 {sample['message']}")
    print(f"  error:                  {err['message']}")


if __name__ == "__main__":
    main()
