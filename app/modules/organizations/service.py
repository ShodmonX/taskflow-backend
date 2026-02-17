import uuid
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.redis import redis_get_json, redis_set_json, redis_del
from app.modules.organizations.enums import OrgRole
from app.modules.organizations.models import Organization, OrgMember
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.invites import generate_invite_token, hash_invite_token, invite_key


ALLOWED_ROLES = {r.value for r in OrgRole}

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

    async def list_members(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID) -> list[OrgMember]:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value, OrgRole.MEMBER.value})
        return await self.repo.list_members(db, org_id)

    async def add_member(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value})

        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")

        existing = await self.repo.get_member(db, org_id, user_id)
        if existing:
            raise HTTPException(status_code=409, detail="User already a member")

        await self.repo.add_member(db, OrgMember(org_id=org_id, user_id=user_id, role=role))
        await db.commit()

    async def change_role(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value})

        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")

        updated = await self.repo.update_role(db, org_id, user_id, role)
        if not updated:
            raise HTTPException(status_code=404, detail="Member not found")
        await db.commit()

    async def remove_member(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value})

        removed = await self.repo.remove_member(db, org_id, user_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Member not found")
        await db.commit()

    async def create_invite(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        role: str,
        ttl_seconds: int | None,
    ) -> tuple[str, int]:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value})

        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")

        ttl = ttl_seconds or settings.invite_token_ttl_seconds

        token = generate_invite_token()
        h = hash_invite_token(token)

        payload = {
            "org_id": str(org_id),
            "role": role,
            "created_by": str(requester_id),
        }
        await redis_set_json(invite_key(h), payload, ttl_seconds=ttl)

        return token, ttl

    async def join_by_invite(
        self,
        db: AsyncSession,
        invite_token: str,
        user_id: uuid.UUID,
    ) -> uuid.UUID:
        h = hash_invite_token(invite_token)
        key = invite_key(h)

        data = await redis_get_json(key)
        if not data:
            raise HTTPException(status_code=404, detail="Invite token is invalid or expired")

        await redis_del(key)

        org_id = uuid.UUID(data["org_id"])
        role = data["role"]

        if await self.repo.get_member(db, org_id, user_id):
            raise HTTPException(status_code=409, detail="Already a member of this organization")

        await self.repo.add_member(db, OrgMember(org_id=org_id, user_id=user_id, role=role))
        await db.commit()

        return org_id

