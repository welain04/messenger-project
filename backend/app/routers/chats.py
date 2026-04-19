from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from .. import storage
from ..deps import get_current_user
from ..models import Chat, Notification, UserInDB, UserRole
from ..schemas import (
    AddParticipantRequest,
    ChatCreateRequest,
    ChatDetail,
    ChatListItem,
    MessagePreview,
)

router = APIRouter(prefix="/chats", tags=["chats"])


def _get_chat_or_404(chat_id: UUID) -> Chat:
    chat = storage.chats.get(chat_id)
    if not chat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return chat


def _ensure_participant(chat: Chat, user: UserInDB) -> None:
    if user.id not in chat.participant_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a participant of this chat")


def _ensure_can_manage(chat: Chat, user: UserInDB) -> None:
    if user.id != chat.created_by and user.role != UserRole.curator:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only chat creator or curator can manage this chat",
        )


def _build_preview(chat: Chat) -> MessagePreview | None:
    msg_ids = storage.messages_by_chat.get(chat.id, [])
    if not msg_ids:
        return None
    last = storage.messages.get(msg_ids[-1])
    if not last:
        return None
    return MessagePreview(
        id=last.id,
        author_id=last.author_id,
        text=last.text,
        sent_at=last.sent_at,
    )


def _unread_count(chat: Chat, user: UserInDB) -> int:
    cnt = 0
    for mid in storage.messages_by_chat.get(chat.id, []):
        m = storage.messages.get(mid)
        if m and not m.is_read and m.author_id != user.id:
            cnt += 1
    return cnt


@router.post("", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreateRequest,
    current: UserInDB = Depends(get_current_user),
) -> ChatDetail:
    participants = list(dict.fromkeys([current.id, *payload.participant_ids]))

    for pid in participants:
        if pid not in storage.users:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"User {pid} not found")

    if payload.type == "personal":
        if len(participants) != 2:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Personal chat must have exactly 2 participants",
            )
    else:
        if len(participants) < 2:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Group chat must have at least 2 participants",
            )

    chat = Chat(
        type=payload.type,
        title=payload.title if payload.type == "group" else None,
        participant_ids=participants,
        created_by=current.id,
    )
    storage.add_chat(chat)

    for pid in participants:
        if pid == current.id:
            continue
        storage.add_notification(
            Notification(user_id=pid, message=f"You were added to a chat: {chat.title or 'personal'}")
        )

    return ChatDetail.model_validate(chat)


@router.get("", response_model=list[ChatListItem])
def list_chats(current: UserInDB = Depends(get_current_user)) -> list[ChatListItem]:
    chat_ids = storage.chats_by_user.get(current.id, set())
    items: list[ChatListItem] = []
    for cid in chat_ids:
        chat = storage.chats.get(cid)
        if not chat:
            continue
        item = ChatListItem(
            id=chat.id,
            type=chat.type,
            title=chat.title,
            participant_ids=chat.participant_ids,
            created_by=chat.created_by,
            created_at=chat.created_at,
            last_message=_build_preview(chat),
            unread_count=_unread_count(chat, current),
        )
        items.append(item)
    items.sort(
        key=lambda c: (c.last_message.sent_at if c.last_message else c.created_at),
        reverse=True,
    )
    return items


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: UUID, current: UserInDB = Depends(get_current_user)) -> ChatDetail:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)
    return ChatDetail(
        id=chat.id,
        type=chat.type,
        title=chat.title,
        participant_ids=chat.participant_ids,
        created_by=chat.created_by,
        created_at=chat.created_at,
        last_message=_build_preview(chat),
        unread_count=_unread_count(chat, current),
    )


@router.post("/{chat_id}/participants", response_model=ChatDetail)
def add_participant(
    chat_id: UUID,
    payload: AddParticipantRequest,
    current: UserInDB = Depends(get_current_user),
) -> ChatDetail:
    chat = _get_chat_or_404(chat_id)
    _ensure_can_manage(chat, current)
    if chat.type != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only group chats support adding participants")
    if payload.user_id not in storage.users:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if payload.user_id in chat.participant_ids:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a participant")

    storage.add_participant(chat, payload.user_id)
    storage.add_notification(
        Notification(user_id=payload.user_id, message=f"You were added to a chat: {chat.title}")
    )
    return ChatDetail(
        id=chat.id,
        type=chat.type,
        title=chat.title,
        participant_ids=chat.participant_ids,
        created_by=chat.created_by,
        created_at=chat.created_at,
        last_message=_build_preview(chat),
        unread_count=_unread_count(chat, current),
    )


@router.delete("/{chat_id}/participants/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant(
    chat_id: UUID,
    user_id: UUID,
    current: UserInDB = Depends(get_current_user),
) -> None:
    chat = _get_chat_or_404(chat_id)
    _ensure_can_manage(chat, current)
    if chat.type != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only group chats support removing participants")
    if user_id not in chat.participant_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User is not a participant")
    if user_id == chat.created_by:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove chat creator")

    storage.remove_participant(chat, user_id)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: UUID, current: UserInDB = Depends(get_current_user)) -> None:
    chat = _get_chat_or_404(chat_id)
    _ensure_can_manage(chat, current)
    storage.remove_chat(chat)
