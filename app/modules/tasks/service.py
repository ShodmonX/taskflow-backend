import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.enums import OrgRole
from app.modules.organizations.service import OrganizationService
from app.modules.organizations.repository import OrganizationRepository
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
        self.org_repo = OrganizationRepository()

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
    
    async def update_task(
        self,
        db: AsyncSession,
        *,
        task_id: uuid.UUID,
        requester_id: uuid.UUID,
        data: dict,
    ) -> Task:
        task = await self.repo.get(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        requester_member = await self.org_repo.get_member(db, task.org_id, requester_id)
        if not requester_member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        is_admin = requester_member.role in {OrgRole.OWNER.value, OrgRole.ADMIN.value}
        is_assignee = task.assigned_to == requester_id

        if "status" in data:
            status = data["status"]
            if status is not None and status not in ALLOWED_STATUSES:
                raise HTTPException(status_code=400, detail="Invalid status")
            if not (is_admin or is_assignee):
                raise HTTPException(status_code=403, detail="Only assignee or admin can change status")

        if "assigned_to" in data:
            if not is_admin:
                raise HTTPException(status_code=403, detail="Only admin can assign tasks")

            assignee = data["assigned_to"]
            if assignee is not None:
                if not await self.org_repo.get_member(db, task.org_id, assignee):
                    raise HTTPException(status_code=400, detail="Assignee is not a member of this organization")

        updated = await self.repo.update_task(db, task_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")
        await db.commit()
        return updated
    
    async def get_task(self, db: AsyncSession, task_id: uuid.UUID, requester_id: uuid.UUID) -> Task:
        task = await self.repo.get(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        requester_member = await self.org_repo.get_member(db, task.org_id, requester_id)
        if not requester_member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        return task