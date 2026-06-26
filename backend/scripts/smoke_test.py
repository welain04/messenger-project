"""Быстрый сквозной smoke-тест основных сценариев.

Использует отдельный файл БД (.smoke_test.db), чтобы не затирать messenger.db
с тестовыми/seed-данными для разработки.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Важно: задать путь до импорта app (get_settings читает env при первом вызове).
os.environ.setdefault("DATABASE_PATH", str(ROOT / ".smoke_test.db"))
# Отключаем rate limiting в smoke-тесте (много логинов с одного "IP").
os.environ.setdefault("RATE_LIMIT_LOGIN_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_REGISTER_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_SEARCH_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_VERIFY_PER_MIN", "0")
os.environ.setdefault("RATE_LIMIT_FORGOT_PASSWORD_PER_MIN", "0")

from fastapi.testclient import TestClient  # noqa: E402

from app import db, mailer, storage  # noqa: E402
from app.main import app  # noqa: E402
from app.models import UserRole  # noqa: E402


def _register_and_verify(c, nickname: str, first: str, last: str) -> dict:
    r = c.post(
        "/api/v1/auth/register",
        json={
            "nickname": nickname,
            "password": "secret1",
            "email": f"{nickname}@example.com",
            "first_name": first,
            "last_name": last,
        },
    )
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["role"] == "student" and user["email_verified"] is False, user
    token = mailer.outbox[-1]["token"]
    r = c.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200 and r.json()["email_verified"] is True, r.text
    return user


def main() -> None:
    db.init_db()
    storage.reset_storage()
    c = TestClient(app)

    alice = _register_and_verify(c, "alice", "Alice", "Anderson")
    bob = _register_and_verify(c, "bob", "Bob", "Brown")

    # Повышение роли — админское действие (через storage, а не через регистрацию).
    storage.set_role(UUID(bob["id"]), UserRole.curator)

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
    assert r.status_code == 403, r.text

    r = c.delete(f"/api/v1/messages/{msg['id']}", headers=a_h)
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

    # ---- Email gating ----
    # Неподтверждённый пользователь не может создавать чаты / отправлять сообщения.
    r = c.post(
        "/api/v1/auth/register",
        json={
            "nickname": "mallory",
            "password": "secret1",
            "email": "mallory@example.com",
            "first_name": "Mallory",
            "last_name": "Quinn",
        },
    )
    assert r.status_code == 201, r.text
    r = c.post("/api/v1/auth/login", json={"nickname": "mallory", "password": "secret1"})
    m_h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = c.post(
        "/api/v1/chats",
        json={"type": "personal", "participant_ids": [bob["id"]]},
        headers=m_h,
    )
    assert r.status_code == 403, r.text  # email не подтверждён

    # Сразу после регистрации повторная отправка письма заблокирована cooldown.
    r = c.post("/api/v1/auth/resend-verification", headers=m_h)
    assert r.status_code == 429, r.text

    # Невалидный токен подтверждения отклоняется.
    r = c.post("/api/v1/auth/verify-email", json={"token": "deadbeef"})
    assert r.status_code == 400, r.text

    # ---- RBAC / admin ----
    # alice (student) не имеет доступа к админским эндпоинтам.
    r = c.get("/api/v1/admin/users", headers=a_h)
    assert r.status_code == 403, r.text

    # Заводим админа напрямую (как сидинг) и логинимся.
    admin_user = _register_and_verify(c, "topadmin", "Top", "Admin")
    storage.set_role(UUID(admin_user["id"]), UserRole.admin)
    r = c.post("/api/v1/auth/login", json={"nickname": "topadmin", "password": "secret1"})
    root_h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = c.get("/api/v1/admin/users", headers=root_h)
    assert r.status_code == 200 and len(r.json()) >= 3, r.text

    # Админ повышает alice до curator.
    r = c.patch(f"/api/v1/admin/users/{alice['id']}/role", json={"role": "curator"}, headers=root_h)
    assert r.status_code == 200 and r.json()["role"] == "curator", r.text

    # Админ не может менять собственную роль.
    r = c.patch(f"/api/v1/admin/users/{admin_user['id']}/role", json={"role": "student"}, headers=root_h)
    assert r.status_code == 400, r.text

    # Блокировка пользователя: его токен перестаёт работать (403).
    r = c.post(f"/api/v1/admin/users/{bob['id']}/suspend", headers=root_h)
    assert r.status_code == 200 and r.json()["is_active"] is False, r.text
    r = c.get("/api/v1/users/me", headers=b_h)
    assert r.status_code == 403, r.text

    # Разблокировка возвращает доступ.
    r = c.post(f"/api/v1/admin/users/{bob['id']}/activate", headers=root_h)
    assert r.status_code == 200 and r.json()["is_active"] is True, r.text
    r = c.get("/api/v1/users/me", headers=b_h)
    assert r.status_code == 200, r.text

    # ---- Заявки на повышение роли + аудит ----
    newbie = _register_and_verify(c, "newbie", "New", "Bee")
    nb_h = {
        "Authorization": "Bearer "
        + c.post("/api/v1/auth/login", json={"nickname": "newbie", "password": "secret1"}).json()["access_token"]
    }
    r = c.post("/api/v1/users/me/role-upgrade-request", json={"reason": "хочу помогать"}, headers=nb_h)
    assert r.status_code == 201 and r.json()["status"] == "pending", r.text
    req_id = r.json()["id"]
    # Повторная заявка отклоняется (уже есть pending).
    r = c.post("/api/v1/users/me/role-upgrade-request", json={}, headers=nb_h)
    assert r.status_code == 409, r.text

    # Админ видит заявку и одобряет её.
    r = c.get("/api/v1/admin/role-upgrade-requests", params={"status": "pending"}, headers=root_h)
    assert r.status_code == 200 and any(x["id"] == req_id for x in r.json()), r.text
    r = c.post(f"/api/v1/admin/role-upgrade-requests/{req_id}/approve", json={"note": "ок"}, headers=root_h)
    assert r.status_code == 200 and r.json()["status"] == "approved", r.text

    # newbie теперь curator.
    r = c.get("/api/v1/users/me", headers=nb_h)
    assert r.status_code == 200 and r.json()["role"] == "curator", r.text

    # Аудит содержит запись об одобрении.
    r = c.get("/api/v1/admin/audit-logs", params={"action": "role_request.approved"}, headers=root_h)
    assert r.status_code == 200 and len(r.json()) >= 1, r.text

    # Заявку можно отклонить.
    newbie2 = _register_and_verify(c, "newbie2", "New", "Two")
    nb2_h = {
        "Authorization": "Bearer "
        + c.post("/api/v1/auth/login", json={"nickname": "newbie2", "password": "secret1"}).json()["access_token"]
    }
    r = c.post("/api/v1/users/me/role-upgrade-request", json={}, headers=nb2_h)
    req2_id = r.json()["id"]
    r = c.post(f"/api/v1/admin/role-upgrade-requests/{req2_id}/reject", json={"note": "позже"}, headers=root_h)
    assert r.status_code == 200 and r.json()["status"] == "rejected", r.text
    r = c.get("/api/v1/users/me", headers=nb2_h)
    assert r.json()["role"] == "student", r.text

    # Ученик без прав не видит аудит/заявки.
    r = c.get("/api/v1/admin/audit-logs", headers=nb2_h)
    assert r.status_code == 403, r.text

    # ---- Refresh-токены и сессии ----
    r = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret1"})
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"], tokens
    old_refresh = tokens["refresh_token"]
    a2_h = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Сессия видна в списке и помечена текущей.
    r = c.get("/api/v1/users/me/sessions", headers=a2_h)
    assert r.status_code == 200 and any(s["current"] for s in r.json()), r.text

    # Refresh выдаёт новую пару; старый refresh инвалидируется (ротация).
    r = c.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200, r.text
    new_tokens = r.json()
    assert new_tokens["refresh_token"] != old_refresh, new_tokens
    r = c.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 401, r.text  # повторное использование старого refresh

    # Logout отзывает сессию: её refresh больше не работает.
    r = c.post("/api/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]})
    assert r.status_code == 204, r.text
    r = c.post("/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]})
    assert r.status_code == 401, r.text

    # Logout-all завершает все сессии пользователя.
    r1 = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret1"}).json()
    r2 = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret1"}).json()
    h_all = {"Authorization": f"Bearer {r1['access_token']}"}
    r = c.post("/api/v1/auth/logout-all", headers=h_all)
    assert r.status_code == 204, r.text
    for t in (r1, r2):
        rr = c.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
        assert rr.status_code == 401, rr.text

    # Блокировка завершает сессии: refresh перестаёт работать.
    victor = _register_and_verify(c, "victor", "Victor", "Vega")
    vr = c.post("/api/v1/auth/login", json={"nickname": "victor", "password": "secret1"}).json()
    r = c.post(f"/api/v1/admin/users/{victor['id']}/suspend", headers=root_h)
    assert r.status_code == 200, r.text
    rr = c.post("/api/v1/auth/refresh", json={"refresh_token": vr["refresh_token"]})
    assert rr.status_code == 401, rr.text

    # --- Смена пароля (авторизованный пользователь) ---
    ar = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret1"}).json()
    ah = {"Authorization": f"Bearer {ar['access_token']}"}
    r = c.patch(
        "/api/v1/users/me/password",
        headers=ah,
        json={"current_password": "secret1", "new_password": "secret2"},
    )
    assert r.status_code == 204, r.text
    r = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret1"})
    assert r.status_code == 401, r.text
    r = c.post("/api/v1/auth/login", json={"nickname": "alice", "password": "secret2"})
    assert r.status_code == 200, r.text
    # вернуть пароль alice для последующих прогонов в той же БД (не критично для smoke)
    ar2 = r.json()
    ah2 = {"Authorization": f"Bearer {ar2['access_token']}"}
    c.patch(
        "/api/v1/users/me/password",
        headers=ah2,
        json={"current_password": "secret2", "new_password": "secret1"},
    )

    # --- Восстановление пароля по email ---
    reset_user = _register_and_verify(c, "resetme", "Reset", "Me")
    r = c.post(
        "/api/v1/auth/forgot-password",
        json={"email": reset_user["email"]},
    )
    assert r.status_code == 202, r.text
    reset_token = mailer.outbox[-1]["token"]
    r = c.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "newpass9"},
    )
    assert r.status_code == 204, r.text
    r = c.post("/api/v1/auth/login", json={"nickname": "resetme", "password": "secret1"})
    assert r.status_code == 401, r.text
    r = c.post("/api/v1/auth/login", json={"nickname": "resetme", "password": "newpass9"})
    assert r.status_code == 200, r.text

    print("SMOKE TEST: OK")


if __name__ == "__main__":
    main()
