from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import audit, storage
from ..deps import get_current_user, require_verified_email
from ..models import Chat, Message, Notification, UserInDB
from ..permissions import Permission, has_permission
from ..schemas import MessageCreateRequest, MessageOut, MessageUpdateRequest

router = APIRouter(tags=["messages"])


def _get_chat_or_404(chat_id: UUID) -> Chat:
    chat = storage.get_chat(chat_id)
    if not chat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Чат не найден")
    return chat


def _get_message_or_404(message_id: UUID) -> Message:
    msg = storage.get_message(message_id)
    if not msg:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сообщение не найдено")
    return msg


def _ensure_participant(chat: Chat, user: UserInDB) -> None:
    if user.id not in chat.participant_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник этого чата")


@router.get("/chats/{chat_id}/messages", response_model=list[MessageOut])
def list_messages(
    chat_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current: UserInDB = Depends(get_current_user),
) -> list[MessageOut]:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)

    # Открытие чата отмечает его прочитанным (водяной знак участника).
    storage.mark_chat_read(chat_id, current.id)
    items = storage.list_messages(chat_id, limit=limit, offset=offset)
    return [MessageOut.model_validate(m) for m in items]


@router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    chat_id: UUID,
    payload: MessageCreateRequest,
    current: UserInDB = Depends(require_verified_email),
) -> MessageOut:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)

    msg = Message(chat_id=chat_id, author_id=current.id, text=payload.text)
    storage.create_message(msg)

    for pid in chat.participant_ids:
        if pid == current.id:
            continue
        storage.create_notification(
            Notification(
                user_id=pid,
                message=f"New message in chat {chat.title or 'personal'}",
            ),
            ntype="new_message",
            actor_id=current.id,
            chat_id=chat_id,
            message_id=msg.id,
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
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Редактировать сообщение может только автор")
    storage.update_message(message_id, payload.text)
    return MessageOut.model_validate(_get_message_or_404(message_id))


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    current: UserInDB = Depends(get_current_user),
) -> None:
    msg = _get_message_or_404(message_id)
    is_author = msg.author_id == current.id
    if not is_author and not has_permission(current.role, Permission.DELETE_ANY_MESSAGE):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Удалить сообщение может только автор или куратор",
        )
    storage.soft_delete_message(message_id)
    if not is_author:
        # Удаление чужого сообщения модератором — фиксируем в аудите.
        audit.record(
            "message.deleted_by_moderator",
            "message",
            actor_id=current.id,
            entity_id=message_id,
            data={"chat_id": str(msg.chat_id), "author_id": str(msg.author_id)},
        )
