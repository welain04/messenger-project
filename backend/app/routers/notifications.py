from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from .. import storage
from ..deps import get_current_user
from ..models import UserInDB
from ..schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(current: UserInDB = Depends(get_current_user)) -> list[NotificationOut]:
    ids = storage.notifications_by_user.get(current.id, [])
    items = [storage.notifications[i] for i in ids if i in storage.notifications]
    items.sort(key=lambda n: n.created_at, reverse=True)
    return [NotificationOut.model_validate(n) for n in items]


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: UUID,
    current: UserInDB = Depends(get_current_user),
) -> NotificationOut:
    n = storage.notifications.get(notification_id)
    if not n:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if n.user_id != current.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your notification")
    n.is_read = True
    return NotificationOut.model_validate(n)
