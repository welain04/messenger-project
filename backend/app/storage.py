"""In-memory хранилище со вспомогательными индексами.

В проде заменим на репозитории поверх БД, сейчас — обычные dict'ы.
"""

from __future__ import annotations

from collections import defaultdict
from threading import RLock
from uuid import UUID

from .models import Chat, Message, Notification, UserInDB

users: dict[UUID, UserInDB] = {}
chats: dict[UUID, Chat] = {}
messages: dict[UUID, Message] = {}
notifications: dict[UUID, Notification] = {}

user_by_nickname: dict[str, UUID] = {}
chats_by_user: dict[UUID, set[UUID]] = defaultdict(set)
messages_by_chat: dict[UUID, list[UUID]] = defaultdict(list)
notifications_by_user: dict[UUID, list[UUID]] = defaultdict(list)

# RLock на случай многопоточного доступа из uvicorn workers (в одном процессе).
lock = RLock()


def reset_storage() -> None:
    """Полная очистка — пригодится для тестов."""
    with lock:
        users.clear()
        chats.clear()
        messages.clear()
        notifications.clear()
        user_by_nickname.clear()
        chats_by_user.clear()
        messages_by_chat.clear()
        notifications_by_user.clear()


def add_user(user: UserInDB) -> None:
    with lock:
        users[user.id] = user
        user_by_nickname[user.nickname.lower()] = user.id


def rename_user(user: UserInDB, new_nickname: str) -> None:
    with lock:
        user_by_nickname.pop(user.nickname.lower(), None)
        user.nickname = new_nickname
        user_by_nickname[new_nickname.lower()] = user.id


def add_chat(chat: Chat) -> None:
    with lock:
        chats[chat.id] = chat
        for pid in chat.participant_ids:
            chats_by_user[pid].add(chat.id)


def remove_chat(chat: Chat) -> None:
    with lock:
        chats.pop(chat.id, None)
        for pid in chat.participant_ids:
            chats_by_user[pid].discard(chat.id)
        for mid in messages_by_chat.pop(chat.id, []):
            messages.pop(mid, None)


def add_participant(chat: Chat, user_id: UUID) -> None:
    with lock:
        if user_id not in chat.participant_ids:
            chat.participant_ids.append(user_id)
        chats_by_user[user_id].add(chat.id)


def remove_participant(chat: Chat, user_id: UUID) -> None:
    with lock:
        if user_id in chat.participant_ids:
            chat.participant_ids.remove(user_id)
        chats_by_user[user_id].discard(chat.id)


def add_message(msg: Message) -> None:
    with lock:
        messages[msg.id] = msg
        messages_by_chat[msg.chat_id].append(msg.id)


def remove_message(msg: Message) -> None:
    with lock:
        messages.pop(msg.id, None)
        if msg.id in messages_by_chat.get(msg.chat_id, []):
            messages_by_chat[msg.chat_id].remove(msg.id)


def add_notification(n: Notification) -> None:
    with lock:
        notifications[n.id] = n
        notifications_by_user[n.user_id].append(n.id)
