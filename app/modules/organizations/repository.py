import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.models import Organization, OrgMember


class OrganizationRepository:
    async def create_org(self, db: AsyncSession, org: Organization) -> Organization:
        db.add(org)
        await db.flush()
        return org

    async def add_member(self, db: AsyncSession, member: OrgMember) -> OrgMember:
        db.add(member)
        await db.flush()
        return member

    async def list_user_orgs(self, db: AsyncSession, user_id: uuid.UUID) -> list[Organization]:
        q = (
            select(Organization)
            .join(OrgMember, OrgMember.org_id == Organization.id)
            .where(OrgMember.user_id == user_id)
            .order_by(Organization.created_at.desc())
        )
        res = await db.execute(q)
        return list(res.scalars().all())

    async def get_member(self, db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> OrgMember | None:
        res = await db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
        )
        return res.scalar_one_or_none()
