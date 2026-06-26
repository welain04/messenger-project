from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .. import audit, storage
from ..deps import get_current_user, require_verified_email
from ..deps_storage import get_file_service
from ..models import Chat, Message, Notification, UserInDB, UserRole
from ..permissions import Permission, has_permission
from ..schemas import AttachmentOut, MessageCreateRequest, MessageOut, MessageUpdateRequest, SignedUrlOut
from ..services.files import FileService

router = APIRouter(tags=["messages"])

_OWN_MESSAGE_DELETE_WINDOW = timedelta(hours=24)


def _within_own_message_delete_window(sent_at: datetime) -> bool:
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - sent_at <= _OWN_MESSAGE_DELETE_WINDOW


def _message_to_out(msg: Message) -> MessageOut:
    return MessageOut(
        id=msg.id,
        chat_id=msg.chat_id,
        author_id=msg.author_id,
        text=msg.text,
        sent_at=msg.sent_at,
        is_read=msg.is_read,
        edited_at=msg.edited_at,
        attachments=[AttachmentOut.model_validate(a) for a in msg.attachments],
    )


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
    return [_message_to_out(m) for m in items]


@router.post(
    "/chats/{chat_id}/messages",
    response_model=MessageOut,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    chat_id: UUID,
    payload: MessageCreateRequest,
    current: UserInDB = Depends(require_verified_email),
    files: FileService = Depends(get_file_service),
) -> MessageOut:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)

    if payload.upload_ids:
        msg, attachments = files.create_message_with_attachments(
            chat_id, current, payload.text, payload.upload_ids
        )
        msg.attachments = attachments
    else:
        text = (payload.text or "").strip()
        msg = Message(chat_id=chat_id, author_id=current.id, text=text)
        storage.create_message(msg, body=text)

    notification_text = (
        f"Новое сообщение в чате «{chat.title}»"
        if chat.type == "group" and chat.title
        else "Новое сообщение в личном чате"
    )
    for pid in chat.participant_ids:
        if pid == current.id:
            continue
        storage.create_notification(
            Notification(
                user_id=pid,
                message=notification_text,
            ),
            ntype="new_message",
            actor_id=current.id,
            chat_id=chat_id,
            message_id=msg.id,
        )
    if not msg.attachments and payload.upload_ids:
        msg = storage.get_message(msg.id) or msg
    return _message_to_out(msg)


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
    return _message_to_out(_get_message_or_404(message_id))


@router.get("/attachments/{attachment_id}/url", response_model=SignedUrlOut | None)
def get_attachment_url(
    attachment_id: UUID,
    current: UserInDB = Depends(get_current_user),
    files: FileService = Depends(get_file_service),
) -> SignedUrlOut | None:
    signed = files.get_attachment_signed_url(attachment_id, current)
    if signed is None:
        return None
    return SignedUrlOut(url=signed.url, expires_at=signed.expires_at, storage_key=signed.storage_key)


@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    current: UserInDB = Depends(get_current_user),
) -> None:
    msg = _get_message_or_404(message_id)
    chat = _get_chat_or_404(msg.chat_id)
    is_author = msg.author_id == current.id

    if is_author:
        if not _within_own_message_delete_window(msg.sent_at):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Удалить своё сообщение можно только в течение 24 часов после отправки",
            )
    elif current.role == UserRole.admin and has_permission(
        current.role, Permission.DELETE_ANY_MESSAGE
    ):
        pass
    elif (
        current.role == UserRole.curator
        and chat.type == "group"
        and chat.created_by == current.id
    ):
        pass
    else:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Удалить чужое сообщение может только создатель группового чата (куратор) "
            "или администратор; в личных чатах — только свои сообщения в течение 24 часов",
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
