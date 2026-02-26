import json
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.deps import get_current_user
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import (
    NotificationListResponse,
    NotificationMarkAllReadResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])
service = NotificationService()


def _to_response(notification: Notification) -> NotificationResponse:
    try:
        payload = json.loads(notification.payload)
    except json.JSONDecodeError:
        payload = {"raw": notification.payload}
    if not isinstance(payload, dict):
        payload = {"value": payload}

    return NotificationResponse(
        id=notification.id,
        type=notification.type,
        payload=payload,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> NotificationListResponse:
    items, total = await service.list_notifications(
        db,
        user_id=user.id,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )
    return NotificationListResponse(
        items=[_to_response(item) for item in items],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> NotificationResponse:
    notification = await service.mark_read(db, notification_id=notification_id, user_id=user.id)
    return _to_response(notification)


@router.patch("/read-all", response_model=NotificationMarkAllReadResponse)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> NotificationMarkAllReadResponse:
    updated = await service.mark_all_read(db, user_id=user.id)
    return NotificationMarkAllReadResponse(updated=updated)


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def unread_notifications_count(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> NotificationUnreadCountResponse:
    unread = await service.unread_count(db, user_id=user.id)
    return NotificationUnreadCountResponse(unread=unread)
