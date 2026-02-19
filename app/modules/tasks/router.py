from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.deps import get_current_user
from app.modules.tasks.schemas import TaskCreateRequest, TaskListResponse, TaskResponse
from app.modules.tasks.service import TaskService
from app.modules.users.models import User

router = APIRouter(tags=["tasks"])
service = TaskService()


@router.post("/orgs/{org_id}/projects/{project_id}/tasks", response_model=TaskResponse)
async def create_task(
    org_id: UUID,
    project_id: UUID,
    payload: TaskCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> TaskResponse:
    t = await service.create_task(
        db,
        org_id=org_id,
        project_id=project_id,
        requester_id=user.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
    )
    return TaskResponse(
        id=t.id, org_id=t.org_id, project_id=t.project_id,
        title=t.title, description=t.description, status=t.status, created_by=t.created_by
    )


@router.get("/orgs/{org_id}/tasks", response_model=TaskListResponse)
async def list_tasks(
    org_id: UUID,
    project_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> TaskListResponse:
    items, total = await service.list_tasks(
        db,
        org_id=org_id,
        requester_id=user.id,
        project_id=project_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return TaskListResponse(
        items=[TaskResponse(
            id=t.id, org_id=t.org_id, project_id=t.project_id,
            title=t.title, description=t.description, status=t.status, created_by=t.created_by
        ) for t in items],
        limit=limit,
        offset=offset,
        total=total,
    )
