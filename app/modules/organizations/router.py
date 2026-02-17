from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.modules.auth.deps import get_current_user
from app.modules.organizations.schemas import OrgCreateRequest, OrgListResponse, OrgResponse
from app.modules.organizations.service import OrganizationService
from app.modules.users.models import User

router = APIRouter(prefix="/orgs", tags=["organizations"])
service = OrganizationService()


@router.post("", response_model=OrgResponse)
async def create_org(
    payload: OrgCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> OrgResponse:
    org = await service.create_organization(db, name=payload.name, creator_id=user.id)
    return OrgResponse(id=org.id, name=org.name, created_by=org.created_by)


@router.get("", response_model=OrgListResponse)
async def my_orgs(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> OrgListResponse:
    orgs = await service.list_my_orgs(db, user.id)
    return OrgListResponse(items=[OrgResponse(id=o.id, name=o.name, created_by=o.created_by) for o in orgs])
