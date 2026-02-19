import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.enums import OrgRole
from app.modules.organizations.service import OrganizationService
from app.modules.projects.repository import ProjectRepository
from app.modules.tasks.models import Task
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import ALLOWED_STATUSES


class TaskService:
    def __init__(
        self,
        repo: TaskRepository | None = None,
        org_service: OrganizationService | None = None,
        project_repo: ProjectRepository | None = None,
    ) -> None:
        self.repo = repo or TaskRepository()
        self.org_service = org_service or OrganizationService()
        self.project_repo = project_repo or ProjectRepository()

    async def create_task(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        requester_id: uuid.UUID,
        title: str,
        description: str | None,
        status: str,
    ) -> Task:
        await self.org_service.require_role(
            db, org_id, requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value, OrgRole.MEMBER.value},
        )

        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")

        project = await self.project_repo.get(db, project_id)
        if not project or project.org_id != org_id:
            raise HTTPException(status_code=404, detail="Project not found in this organization")

        task = Task(
            org_id=org_id,
            project_id=project_id,
            title=title,
            description=description,
            status=status,
            created_by=requester_id,
        )
        await self.repo.create(db, task)
        await db.commit()
        return task

    async def list_tasks(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        project_id: uuid.UUID | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Task], int]:
        await self.org_service.require_role(
            db, org_id, requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value, OrgRole.MEMBER.value},
        )

        if status and status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")

        if project_id:
            project = await self.project_repo.get(db, project_id)
            if not project or project.org_id != org_id:
                raise HTTPException(status_code=404, detail="Project not found in this organization")

        return await self.repo.list(db, org_id=org_id, project_id=project_id, status=status, limit=limit, offset=offset)
