import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification, NotificationOutbox


class NotificationRepository:
    async def list_for_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        is_read: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if is_read is not None:
            stmt = stmt.where(Notification.is_read == is_read)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await db.execute(total_stmt)).scalar_one())

        rows = await db.execute(
            stmt.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        )
        return list(rows.scalars().all()), total

    async def get_for_user(
        self,
        db: AsyncSession,
        *,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification | None:
        rows = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        return rows.scalar_one_or_none()

    async def mark_read(self, db: AsyncSession, notification: Notification) -> Notification:
        notification.is_read = True
        db.add(notification)
        await db.flush()
        return notification

    async def mark_all_read(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        res = cast(
            CursorResult[Any],
            await db.execute(
                update(Notification)
                .where(Notification.user_id == user_id, Notification.is_read.is_(False))
                .values(is_read=True)
            ),
        )
        return res.rowcount or 0

    async def count_unread(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        res = await db.execute(
            select(func.count()).select_from(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return int(res.scalar_one())

    async def enqueue_outbox(self, db: AsyncSession, *, event_type: str, payload: str) -> NotificationOutbox:
        row = NotificationOutbox(event_type=event_type, payload=payload, status="PENDING", attempts=0)
        db.add(row)
        await db.flush()
        return row

    async def claim_outbox_batch(self, db: AsyncSession, *, limit: int) -> list[NotificationOutbox]:
        now = datetime.now(timezone.utc)
        rows = await db.execute(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_(("PENDING", "FAILED")),
                or_(
                    NotificationOutbox.next_retry_at.is_(None),
                    NotificationOutbox.next_retry_at <= now,
                ),
            )
            .order_by(NotificationOutbox.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(rows.scalars().all())

    async def save_outbox_row(self, db: AsyncSession, row: NotificationOutbox) -> NotificationOutbox:
        db.add(row)
        await db.flush()
        return row
