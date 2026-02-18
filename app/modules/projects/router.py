from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.deps import get_current_user
from app.modules.projects.schemas import ProjectCreateRequest, ProjectListResponse, ProjectResponse
from app.modules.projects.service import ProjectService
from app.modules.users.models import User

router = APIRouter(tags=["projects"])
service = ProjectService()


@router.post("/orgs/{org_id}/projects", response_model=ProjectResponse)
async def create_project(
    org_id: UUID,
    payload: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ProjectResponse:
    p = await service.create_project(
        db,
        org_id=org_id,
        requester_id=user.id,
        name=payload.name,
        description=payload.description,
    )
    return ProjectResponse(id=p.id, org_id=p.org_id, name=p.name, description=p.description, created_by=p.created_by)


@router.get("/orgs/{org_id}/projects", response_model=ProjectListResponse)
async def list_projects(
    org_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> ProjectListResponse:
    items = await service.list_projects(db, org_id=org_id, requester_id=user.id)
    return ProjectListResponse(
        items=[ProjectResponse(id=p.id, org_id=p.org_id, name=p.name, description=p.description, created_by=p.created_by) for p in items]
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    await service.delete_project(db, project_id=project_id, requester_id=user.id)
    return {"status": "ok"}
