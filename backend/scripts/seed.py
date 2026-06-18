r"""Наполнение базы тестовыми данными.

Запуск (из папки backend):
    .\.venv\Scripts\python.exe scripts\seed.py

Скрипт идемпотентен: полностью очищает messenger.db и создаёт данные заново.
ВНИМАНИЕ: не запускайте без необходимости — все текущие пользователи и чаты будут удалены.
Все тестовые пользователи имеют пароль: password123
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import db, storage  # noqa: E402
from app.models import Chat, Message, Notification, UserInDB, UserRole  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD = "password123"


def _user(nickname: str, role: UserRole, first_name: str, last_name: str) -> UserInDB:
    user = UserInDB(
        nickname=nickname,
        role=role,
        hashed_password=hash_password(PASSWORD),
        email=f"{nickname}@example.com",
        first_name=first_name,
        last_name=last_name,
        email_verified=True,  # seed-пользователи сразу подтверждены
    )
    storage.create_user(user)
    return user


def main() -> None:
    db.init_db()
    storage.reset_storage()

    now = datetime.now(timezone.utc)

    # --- пользователи ---
    _user("admin", UserRole.admin, "Admin", "Root")
    alice = _user("alice", UserRole.curator, "Alice", "Anderson")
    bob = _user("bob", UserRole.student, "Bob", "Brown")
    carol = _user("carol", UserRole.student, "Carol", "Clark")
    dave = _user("dave", UserRole.student, "Dave", "Davis")

    # --- личный чат alice <-> bob ---
    dm = Chat(type="personal", participant_ids=[alice.id, bob.id], created_by=alice.id)
    storage.create_chat(dm)
    storage.create_message(
        Message(chat_id=dm.id, author_id=alice.id, text="Привет, Bob! Как продвигается задание?",
                sent_at=now - timedelta(minutes=30))
    )
    storage.create_message(
        Message(chat_id=dm.id, author_id=bob.id, text="Привет! Почти закончил, остался последний пункт.",
                sent_at=now - timedelta(minutes=25))
    )

    # --- групповой чат "Math 101" ---
    group = Chat(
        type="group",
        title="Math 101",
        participant_ids=[alice.id, bob.id, carol.id],
        created_by=alice.id,
    )
    storage.create_chat(group)
    storage.create_message(
        Message(chat_id=group.id, author_id=alice.id, text="Добро пожаловать в группу Math 101!",
                sent_at=now - timedelta(minutes=20))
    )
    storage.create_message(
        Message(chat_id=group.id, author_id=carol.id, text="Спасибо! Когда дедлайн по домашке?",
                sent_at=now - timedelta(minutes=15))
    )
    storage.create_message(
        Message(chat_id=group.id, author_id=alice.id, text="В пятницу до 18:00.",
                sent_at=now - timedelta(minutes=10))
    )

    # --- несколько уведомлений ---
    storage.create_notification(
        Notification(user_id=bob.id, message="New message in chat personal", created_at=now - timedelta(minutes=25)),
        ntype="new_message",
    )
    storage.create_notification(
        Notification(user_id=carol.id, message="You were added to a chat: Math 101",
                     created_at=now - timedelta(minutes=20)),
        ntype="added_to_chat",
    )

    print("SEED OK:")
    print(f"  users: admin (admin), alice (curator), bob, carol, dave (student)  | password: {PASSWORD}")
    print(f"  chats: personal alice<->bob, group 'Math 101' (alice, bob, carol)")
    print(f"  db:    {db._db_path()}")


if __name__ == "__main__":
    main()
