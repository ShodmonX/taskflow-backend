import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tasks.models import Task


class TaskRepository:
    async def create(self, db: AsyncSession, task: Task) -> Task:
        db.add(task)
        await db.flush()
        return task

    async def list(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        stmt = select(Task).where(Task.org_id == org_id)

        if project_id:
            stmt = stmt.where(Task.project_id == project_id)
        if status:
            stmt = stmt.where(Task.status == status)

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = int((await db.execute(total_stmt)).scalar_one())

        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)
        rows = await db.execute(stmt)
        return list(rows.scalars().all()), total
