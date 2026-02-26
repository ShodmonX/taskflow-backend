import uuid
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
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

    async def get_org(self, db: AsyncSession, org_id: uuid.UUID) -> Organization | None:
        res = await db.execute(select(Organization).where(Organization.id == org_id))
        return res.scalar_one_or_none()

    async def update_org(self, db: AsyncSession, org: Organization, data: dict) -> Organization:
        for key, value in data.items():
            setattr(org, key, value)
        db.add(org)
        await db.flush()
        return org

    async def delete_org(self, db: AsyncSession, org_id: uuid.UUID) -> int:
        res = cast(
            CursorResult[Any],
            await db.execute(delete(Organization).where(Organization.id == org_id)),
        )
        return res.rowcount or 0

    async def get_member(self, db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> OrgMember | None:
        res = await db.execute(
            select(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)
        )
        return res.scalar_one_or_none()

    async def list_members(self, db: AsyncSession, org_id: uuid.UUID) -> list[OrgMember]:
        res = await db.execute(select(OrgMember).where(OrgMember.org_id == org_id))
        return list(res.scalars().all())

    async def remove_member(self, db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID) -> int:
        res = cast(
            CursorResult[Any],
            await db.execute(delete(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id)),
        )
        return res.rowcount or 0

    async def update_role(self, db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, role: str) -> int:
        res = cast(
            CursorResult[Any],
            await db.execute(
                update(OrgMember).where(OrgMember.org_id == org_id, OrgMember.user_id == user_id).values(role=role)
            ),
        )
        return res.rowcount or 0

    async def count_members_by_role(self, db: AsyncSession, org_id: uuid.UUID, role: str) -> int:
        res = await db.execute(
            select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org_id, OrgMember.role == role)
        )
        return int(res.scalar_one())
