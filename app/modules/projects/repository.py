import uuid
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project


class ProjectRepository:
    async def create(self, db: AsyncSession, project: Project) -> Project:
        db.add(project)
        await db.flush()
        return project

    async def list_by_org(self, db: AsyncSession, org_id: uuid.UUID) -> list[Project]:
        res = await db.execute(
            select(Project).where(Project.org_id == org_id).order_by(Project.created_at.desc())
        )
        return list(res.scalars().all())

    async def get(self, db: AsyncSession, project_id: uuid.UUID) -> Project | None:
        res = await db.execute(select(Project).where(Project.id == project_id))
        return res.scalar_one_or_none()

    async def delete(self, db: AsyncSession, project_id: uuid.UUID) -> int:
        res = cast(
            CursorResult[Any],
            await db.execute(delete(Project).where(Project.id == project_id)),
        )
        return res.rowcount or 0
