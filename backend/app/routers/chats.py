from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from .. import audit, storage
from ..deps import require_verified_email
from ..models import Chat, Notification, UserInDB, UserRole
from ..permissions import Permission, has_permission
from ..schemas import (
    AddParticipantRequest,
    ChatCreateRequest,
    ChatDetail,
    ChatListItem,
    MessagePreview,
)

router = APIRouter(prefix="/chats", tags=["chats"])


def _get_chat_or_404(chat_id: UUID) -> Chat:
    chat = storage.get_chat(chat_id)
    if not chat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Чат не найден")
    return chat


def _ensure_participant(chat: Chat, user: UserInDB) -> None:
    if user.id not in chat.participant_ids:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не участник этого чата")


def _ensure_can_manage_members(chat: Chat, user: UserInDB) -> None:
    # Управлять участниками может создатель чата; администратор — в любом групповом чате.
    # Куратор — только в групповых чатах, которые он сам создал (created_by).
    if user.id == chat.created_by:
        return
    if user.role == UserRole.admin and has_permission(
        user.role, Permission.MANAGE_CHAT_MEMBERS
    ):
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Управлять участниками может создатель чата или администратор",
    )


def _ensure_can_edit_chat(chat: Chat, user: UserInDB) -> None:
    # Изменять/удалять чат может владелец либо обладатель права edit_chat.
    if user.id == chat.created_by:
        return
    if has_permission(user.role, Permission.EDIT_CHAT):
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        "Изменять чат может создатель или куратор",
    )


def _build_preview(chat: Chat) -> MessagePreview | None:
    last = storage.last_message(chat.id)
    if not last:
        return None
    return MessagePreview(
        id=last.id,
        author_id=last.author_id,
        text=last.text,
        sent_at=last.sent_at,
    )


def _to_detail(chat: Chat, current: UserInDB) -> ChatDetail:
    return ChatDetail(
        id=chat.id,
        type=chat.type,
        title=chat.title,
        participant_ids=chat.participant_ids,
        created_by=chat.created_by,
        created_at=chat.created_at,
        last_message=_build_preview(chat),
        unread_count=storage.unread_count(chat.id, current.id),
    )


@router.post("", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreateRequest,
    current: UserInDB = Depends(require_verified_email),
) -> ChatDetail:
    required_perm = (
        Permission.CREATE_GROUP_CHAT if payload.type == "group" else Permission.CREATE_CHAT
    )
    if not has_permission(current.role, required_perm):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Недостаточно прав для создания чата этого типа",
        )

    participants = list(dict.fromkeys([current.id, *payload.participant_ids]))

    for pid in participants:
        if not storage.user_exists(pid):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Пользователь {pid} не найден")

    if payload.type == "personal":
        if len(participants) != 2:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "В личном чате должно быть ровно 2 участника",
            )
        if storage.find_personal_chat(participants) is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Личный чат между этими пользователями уже существует",
            )
    else:
        if len(participants) < 2:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "В групповом чате должно быть не менее 2 участников",
            )

    chat = Chat(
        type=payload.type,
        title=payload.title if payload.type == "group" else None,
        participant_ids=participants,
        created_by=current.id,
    )
    storage.create_chat(chat)

    audit.record(
        "chat.created",
        "chat",
        actor_id=current.id,
        entity_id=chat.id,
        data={"type": chat.type, "participant_count": len(participants)},
    )

    for pid in participants:
        if pid == current.id:
            continue
        storage.create_notification(
            Notification(user_id=pid, message=f"You were added to a chat: {chat.title or 'personal'}"),
            ntype="added_to_chat",
            actor_id=current.id,
            chat_id=chat.id,
        )

    return _to_detail(chat, current)


@router.get("", response_model=list[ChatListItem])
def list_chats(current: UserInDB = Depends(require_verified_email)) -> list[ChatListItem]:
    items: list[ChatListItem] = []
    for chat in storage.list_chats_for_user(current.id):
        items.append(
            ChatListItem(
                id=chat.id,
                type=chat.type,
                title=chat.title,
                participant_ids=chat.participant_ids,
                created_by=chat.created_by,
                created_at=chat.created_at,
                last_message=_build_preview(chat),
                unread_count=storage.unread_count(chat.id, current.id),
            )
        )
    items.sort(
        key=lambda c: (c.last_message.sent_at if c.last_message else c.created_at),
        reverse=True,
    )
    return items


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: UUID, current: UserInDB = Depends(require_verified_email)) -> ChatDetail:
    chat = _get_chat_or_404(chat_id)
    _ensure_participant(chat, current)
    return _to_detail(chat, current)


@router.post("/{chat_id}/participants", response_model=ChatDetail)
def add_participant(
    chat_id: UUID,
    payload: AddParticipantRequest,
    current: UserInDB = Depends(require_verified_email),
) -> ChatDetail:
    chat = _get_chat_or_404(chat_id)
    _ensure_can_manage_members(chat, current)
    if chat.type != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Добавлять участников можно только в групповой чат")
    if not storage.user_exists(payload.user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    if payload.user_id in chat.participant_ids:
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь уже в чате")

    storage.add_participant(chat_id, payload.user_id)
    storage.create_notification(
        Notification(user_id=payload.user_id, message=f"You were added to a chat: {chat.title}"),
        ntype="added_to_chat",
        actor_id=current.id,
        chat_id=chat_id,
    )
    return _to_detail(_get_chat_or_404(chat_id), current)


@router.delete("/{chat_id}/participants/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant(
    chat_id: UUID,
    user_id: UUID,
    current: UserInDB = Depends(require_verified_email),
) -> None:
    chat = _get_chat_or_404(chat_id)
    _ensure_can_manage_members(chat, current)
    if chat.type != "group":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Удалять участников можно только из группового чата")
    if user_id not in chat.participant_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не участник чата")
    if user_id == chat.created_by:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Нельзя удалить создателя чата")

    storage.remove_participant(chat_id, user_id)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: UUID, current: UserInDB = Depends(require_verified_email)) -> None:
    chat = _get_chat_or_404(chat_id)
    _ensure_can_edit_chat(chat, current)
    storage.delete_chat(chat_id)
    audit.record(
        "chat.deleted",
        "chat",
        actor_id=current.id,
        entity_id=chat_id,
        data={"type": chat.type, "by_owner": current.id == chat.created_by},
    )
