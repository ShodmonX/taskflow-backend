import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.enums import OrgRole
from app.modules.organizations.service import OrganizationService
from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository


class ProjectService:
    def __init__(
        self,
        repo: ProjectRepository | None = None,
        org_service: OrganizationService | None = None,
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.org_service = org_service or OrganizationService()

    async def create_project(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Project:
        await self.org_service.require_role(
            db,
            org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value},
        )

        project = Project(org_id=org_id, name=name, description=description, created_by=requester_id)
        await self.repo.create(db, project)
        await db.commit()
        return project

    async def list_projects(self, db: AsyncSession, *, org_id: uuid.UUID, requester_id: uuid.UUID) -> list[Project]:
        await self.org_service.require_role(
            db,
            org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value, OrgRole.MEMBER.value},
        )
        return await self.repo.list_by_org(db, org_id)

    async def delete_project(self, db: AsyncSession, *, project_id: uuid.UUID, requester_id: uuid.UUID) -> None:
        project = await self.repo.get(db, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await self.org_service.require_role(
            db,
            project.org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value},
        )

        deleted = await self.repo.delete(db, project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
        await db.commit()
