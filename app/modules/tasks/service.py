import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.celery_app import celery_app
from app.modules.notifications.service import NotificationService
from app.modules.organizations.enums import OrgRole
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.service import OrganizationService
from app.modules.projects.repository import ProjectRepository
from app.modules.tasks.models import Task
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schemas import ALLOWED_STATUSES


logger = logging.getLogger(__name__)


class TaskService:
    def __init__(
        self,
        repo: TaskRepository | None = None,
        org_service: OrganizationService | None = None,
        project_repo: ProjectRepository | None = None,
        notification_service: NotificationService | None = None,
    ) -> None:
        self.repo = repo or TaskRepository()
        self.org_service = org_service or OrganizationService()
        self.project_repo = project_repo or ProjectRepository()
        self.org_repo = OrganizationRepository()
        self.notification_service = notification_service or NotificationService()

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

        old_assignee = task.assigned_to

        updated = await self.repo.update_task(db, task_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Task not found")

        assignment_event: dict | None = None
        if "assigned_to" in data:
            new_assignee = updated.assigned_to
            if new_assignee and new_assignee != old_assignee:
                assignment_event = {
                    "org_id": str(updated.org_id),
                    "project_id": str(updated.project_id),
                    "task_id": str(updated.id),
                    "assigned_to": str(new_assignee),
                    "assigned_by": str(requester_id),
                    "title": updated.title,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }

                await self.notification_service.enqueue_task_assigned(db, assignment_event)

        await db.commit()

        if assignment_event:
            try:
                await asyncio.to_thread(
                    celery_app.send_task,
                    "taskflow.dispatch_notifications_outbox",
                    kwargs={"limit": 100},
                )
            except Exception:
                logger.exception(
                    "Failed to trigger notifications outbox dispatch",
                    extra={"task_id": str(updated.id), "assigned_to": assignment_event["assigned_to"]},
                )
        return updated

    async def get_task(self, db: AsyncSession, task_id: uuid.UUID, requester_id: uuid.UUID) -> Task:
        task = await self.repo.get(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        requester_member = await self.org_repo.get_member(db, task.org_id, requester_id)
        if not requester_member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        return task

    async def delete_task(self, db: AsyncSession, *, task_id: uuid.UUID, requester_id: uuid.UUID) -> None:
        task = await self.repo.get(db, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        requester_member = await self.org_repo.get_member(db, task.org_id, requester_id)
        if not requester_member:
            raise HTTPException(status_code=403, detail="Not a member of this organization")

        is_admin = requester_member.role in {OrgRole.OWNER.value, OrgRole.ADMIN.value}
        is_creator = task.created_by == requester_id
        if not (is_admin or is_creator):
            raise HTTPException(status_code=403, detail="Only task creator or admin can delete tasks")

        deleted = await self.repo.delete(db, task_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Task not found")
        await db.commit()
