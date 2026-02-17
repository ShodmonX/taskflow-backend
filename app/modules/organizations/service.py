import uuid
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.enums import OrgRole
from app.modules.organizations.models import Organization, OrgMember
from app.modules.organizations.repository import OrganizationRepository


class OrganizationService:
    def __init__(self, repo: OrganizationRepository | None = None) -> None:
        self.repo = repo or OrganizationRepository()

    async def create_organization(self, db: AsyncSession, *, name: str, creator_id: uuid.UUID) -> Organization:
        org = Organization(name=name, created_by=creator_id)
        await self.repo.create_org(db, org)

        owner = OrgMember(org_id=org.id, user_id=creator_id, role=OrgRole.OWNER.value)
        await self.repo.add_member(db, owner)

        await db.commit()
        return org

    async def list_my_orgs(self, db: AsyncSession, user_id: uuid.UUID) -> list[Organization]:
        return await self.repo.list_user_orgs(db, user_id)

    async def require_role(self, db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, allowed: set[str]) -> OrgMember:
        m = await self.repo.get_member(db, org_id, user_id)
        if not m:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        if m.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return m
