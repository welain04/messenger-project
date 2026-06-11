"""Быстрый сквозной smoke-тест основных сценариев.

Использует отдельный файл БД (.smoke_test.db), чтобы не затирать messenger.db
с тестовыми/seed-данными для разработки.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Важно: задать путь до импорта app (get_settings читает env при первом вызове).
os.environ.setdefault("DATABASE_PATH", str(ROOT / ".smoke_test.db"))

from fastapi.testclient import TestClient  # noqa: E402

from app import db, storage  # noqa: E402
from app.main import app  # noqa: E402


def main() -> None:
    db.init_db()
    storage.reset_storage()
    c = TestClient(app)

    r = c.post("/api/v1/auth/register", json={"nickname": "alice", "password": "secret1", "role": "student"})
    assert r.status_code == 201, r.text
    alice = r.json()

    r = c.post("/api/v1/auth/register", json={"nickname": "bob", "password": "secret1", "role": "curator"})
    assert r.status_code == 201, r.text
    bob = r.json()

    r = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret1"})
    assert r.status_code == 200, r.text
    a_tok = r.json()["access_token"]
    a_h = {"Authorization": f"Bearer {a_tok}"}

    r = c.post("/api/v1/auth/login", json={"nickname": "bob", "password": "secret1"})
    b_tok = r.json()["access_token"]
    b_h = {"Authorization": f"Bearer {b_tok}"}

    r = c.get("/api/v1/users/me", headers=a_h)
    assert r.status_code == 200 and r.json()["nickname"] == "alice"

    r = c.post(
        "/api/v1/chats",
        json={"type": "personal", "participant_ids": [bob["id"]]},
        headers=a_h,
    )
    assert r.status_code == 201, r.text
    p_chat = r.json()
    assert len(p_chat["participant_ids"]) == 2

    r = c.post(
        "/api/v1/chats",
        json={
            "type": "group",
            "title": "Vibe Coding",
            "participant_ids": [bob["id"]],
        },
        headers=a_h,
    )
    assert r.status_code == 201, r.text
    g_chat = r.json()

    r = c.post(
        "/api/v1/chats",
        json={"type": "personal", "title": "x", "participant_ids": [bob["id"]]},
        headers=a_h,
    )
    assert r.status_code == 422, r.text

    r = c.post(
        f"/api/v1/chats/{g_chat['id']}/messages",
        json={"text": "Hello bob!"},
        headers=a_h,
    )
    assert r.status_code == 201, r.text
    msg = r.json()

    r = c.patch(
        f"/api/v1/messages/{msg['id']}",
        json={"text": "Hello bob (edited)"},
        headers=b_h,
    )
    assert r.status_code == 403, r.text

    r = c.patch(
        f"/api/v1/messages/{msg['id']}",
        json={"text": "Hello bob (edited)"},
        headers=a_h,
    )
    assert r.status_code == 200 and r.json()["text"] == "Hello bob (edited)"

    r = c.get(f"/api/v1/chats/{g_chat['id']}/messages", headers=b_h)
    assert r.status_code == 200 and len(r.json()) == 1

    r = c.delete(f"/api/v1/messages/{msg['id']}", headers=b_h)
    assert r.status_code == 204, r.text

    r = c.get("/api/v1/chats", headers=a_h)
    assert r.status_code == 200 and len(r.json()) == 2

    r = c.get("/api/v1/notifications", headers=b_h)
    assert r.status_code == 200 and len(r.json()) >= 2
    n = r.json()[0]

    r = c.patch(f"/api/v1/notifications/{n['id']}/read", headers=b_h)
    assert r.status_code == 200 and r.json()["is_read"] is True

    r = c.delete(f"/api/v1/chats/{g_chat['id']}", headers=b_h)
    assert r.status_code == 204, r.text

    print("SMOKE TEST: OK")


if __name__ == "__main__":
    main()
