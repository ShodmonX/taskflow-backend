from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: UUID
    type: str
    payload: dict
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    limit: int
    offset: int
    total: int


class NotificationMarkAllReadResponse(BaseModel):
    updated: int


class NotificationUnreadCountResponse(BaseModel):
    unread: int
