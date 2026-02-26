import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.modules.notifications.models import Notification, NotificationOutbox
from app.modules.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, repo: NotificationRepository | None = None) -> None:
        self.repo = repo or NotificationRepository()

    async def list_notifications(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        is_read: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Notification], int]:
        return await self.repo.list_for_user(
            db,
            user_id=user_id,
            is_read=is_read,
            limit=limit,
            offset=offset,
        )

    async def mark_read(
        self,
        db: AsyncSession,
        *,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification:
        notification = await self.repo.get_for_user(
            db,
            notification_id=notification_id,
            user_id=user_id,
        )
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        if not notification.is_read:
            await self.repo.mark_read(db, notification)
            await db.commit()

        return notification

    async def mark_all_read(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        updated = await self.repo.mark_all_read(db, user_id=user_id)
        await db.commit()
        return updated

    async def unread_count(self, db: AsyncSession, *, user_id: uuid.UUID) -> int:
        return await self.repo.count_unread(db, user_id=user_id)

    async def enqueue_task_assigned(self, db: AsyncSession, event: dict) -> NotificationOutbox:
        return await self.repo.enqueue_outbox(
            db,
            event_type="TASK_ASSIGNED",
            payload=json.dumps(event),
        )

    async def _create_notification_from_event(
        self,
        db: AsyncSession,
        *,
        event_type: str,
        event: dict,
    ) -> Notification:
        if event_type != "TASK_ASSIGNED":
            raise ValueError(f"Unsupported outbox event type: {event_type}")

        notif = Notification(
            user_id=uuid.UUID(event["assigned_to"]),
            type="TASK_ASSIGNED",
            payload=json.dumps(event),
        )
        db.add(notif)
        await db.flush()
        return notif

    async def _create_task_assigned_async(self, event: dict) -> None:
        async with AsyncSessionLocal() as db:
            try:
                await self._create_notification_from_event(db, event_type="TASK_ASSIGNED", event=event)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def _dispatch_outbox_async(self, *, limit: int) -> int:
        async with AsyncSessionLocal() as db:
            rows = await self.repo.claim_outbox_batch(db, limit=limit)
            if not rows:
                return 0

            now = datetime.now(timezone.utc)
            processed = 0
            for row in rows:
                try:
                    event = json.loads(row.payload)
                    if not isinstance(event, dict):
                        raise ValueError("Outbox payload must be a JSON object")

                    await self._create_notification_from_event(
                        db,
                        event_type=row.event_type,
                        event=event,
                    )
                    row.status = "SENT"
                    row.sent_at = now
                    row.last_error = None
                    row.next_retry_at = None
                except Exception as exc:
                    row.attempts += 1
                    row.status = "FAILED"
                    row.last_error = str(exc)[:1000]
                    delay_seconds = min(300, 2 ** min(row.attempts, 8))
                    row.next_retry_at = now + timedelta(seconds=delay_seconds)

                await self.repo.save_outbox_row(db, row)
                processed += 1

            await db.commit()
            return processed

    def create_task_assigned(self, event: dict) -> None:
        asyncio.run(self._create_task_assigned_async(event))

    def dispatch_outbox(self, limit: int = 100) -> int:
        return asyncio.run(self._dispatch_outbox_async(limit=limit))
