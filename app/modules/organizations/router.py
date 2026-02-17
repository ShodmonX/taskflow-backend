from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends

from app.db.session import get_db_session
from app.modules.auth.deps import get_current_user
from app.modules.organizations.schemas import (
    MemberAddRequest, MemberListResponse, MemberResponse, MemberRoleUpdateRequest,
    OrgCreateRequest, OrgListResponse, OrgResponse,
    InviteCreateRequest, InviteCreateResponse, JoinByInviteRequest,
)
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

@router.get("/{org_id}/members", response_model=MemberListResponse)
async def members(org_id: UUID, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    ms = await service.list_members(db, org_id, user.id)
    return MemberListResponse(items=[MemberResponse(user_id=m.user_id, role=m.role) for m in ms])

@router.post("/{org_id}/members")
async def add_member(org_id: UUID, payload: MemberAddRequest, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    await service.add_member(db, org_id, user.id, payload.user_id, payload.role)
    return {"status": "ok"}

@router.patch("/{org_id}/members/{member_user_id}")
async def change_role(org_id: UUID, member_user_id: UUID, payload: MemberRoleUpdateRequest, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    await service.change_role(db, org_id, user.id, member_user_id, payload.role)
    return {"status": "ok"}

@router.delete("/{org_id}/members/{member_user_id}")
async def remove_member(org_id: UUID, member_user_id: UUID, db: AsyncSession = Depends(get_db_session), user: User = Depends(get_current_user)):
    await service.remove_member(db, org_id, user.id, member_user_id)
    return {"status": "ok"}

@router.post("/{org_id}/invites", response_model=InviteCreateResponse)
async def create_invite(
    org_id: UUID,
    payload: InviteCreateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> InviteCreateResponse:
    token, ttl = await service.create_invite(db, org_id, user.id, payload.role, payload.ttl_seconds)
    return InviteCreateResponse(invite_token=token, org_id=org_id, role=payload.role, expires_in=ttl)


@router.post("/join")
async def join_by_invite(
    payload: JoinByInviteRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> dict:
    org_id = await service.join_by_invite(db, payload.invite_token, user.id)
    return {"status": "ok", "org_id": str(org_id)}
