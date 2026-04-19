from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import storage
from ..deps import get_current_user
from ..models import Chat, Message, Notification, UserInDB, UserRole
from ..schemas import MessageCreateRequest, MessageOut, MessageUpdateRequest

router = APIRouter(tags=["messages"])


def _get_chat_or_404(chat_id: UUID) -> Chat:
    chat = storage.chats.get(chat_id)
    if not chat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return chat


def _get_message_or_404(message_id: UUID) -> Message:
    msg = storage.messages.get(message_id)
    if not msg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Message not found")
    return msg


def _ensure_participant(chat: Chat, user: UserInDB) -> None:
    if user.id not in chat.participant_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a participant of this chat")


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(
    chat_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current: UserInDB = Depends(get_current_user),
) -> list[MessageOut]:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)

    ids = storage.messages_by_chat.get(chat_id, [])
    page = ids[offset : offset + limit]
    items: list[MessageOut] = []
    for mid in page:
        m = storage.messages.get(mid)
        if not m:
            continue
        if not m.is_read and m.author_id != current.id:
            m.is_read = True
        items.append(MessageOut.model_validate(m))
    return items


@router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    chat_id: UUID,
    payload: MessageCreateRequest,
    current: UserInDB = Depends(get_current_user),
) -> MessageOut:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)

    msg = Message(chat_id=chat_id, author_id=current.id, text=payload.text)
    storage.add_message(msg)

    for pid in chat.participant_ids:
        if pid == current.id:
            continue
        storage.add_notification(
            Notification(
                user_id=pid,
                message=f"New message in chat {chat.title or 'personal'}",
            )
        )
    return MessageOut.model_validate(msg)


@router.patch("/messages/{message_id}", response_model=MessageOut)
def edit_message(
    message_id: UUID,
    payload: MessageUpdateRequest,
    current: UserInDB = Depends(get_current_user),
) -> MessageOut:
    msg = _get_message_or_404(message_id)
    if msg.author_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can edit the message")
    msg.text = payload.text
    msg.edited_at = datetime.now(timezone.utc)
    return MessageOut.model_validate(msg)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    current: UserInDB = Depends(get_current_user),
) -> None:
    msg = _get_message_or_404(message_id)
    if msg.author_id != current.id and current.role != UserRole.curator:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only author or curator can delete the message",
        )
    storage.remove_message(msg)
