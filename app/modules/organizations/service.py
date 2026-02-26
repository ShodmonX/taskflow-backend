import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infra.redis import (
    redis_del,
    redis_get_json,
    redis_set_add,
    redis_set_json,
    redis_set_members,
    redis_set_remove,
    redis_ttl_seconds,
)
from app.modules.organizations.enums import OrgRole
from app.modules.organizations.models import Organization, OrgMember
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.invites import (
    generate_invite_token,
    hash_invite_token,
    invite_key,
    invites_index_key,
)


ALLOWED_ROLES = {r.value for r in OrgRole}

class OrganizationService:
    def __init__(self, repo: OrganizationRepository | None = None) -> None:
        self.repo = repo or OrganizationRepository()

    async def _count_owners(self, db: AsyncSession, org_id: uuid.UUID) -> int:
        return await self.repo.count_members_by_role(db, org_id, OrgRole.OWNER.value)

    async def create_organization(self, db: AsyncSession, *, name: str, creator_id: uuid.UUID) -> Organization:
        org = Organization(name=name, created_by=creator_id)
        await self.repo.create_org(db, org)

        owner = OrgMember(org_id=org.id, user_id=creator_id, role=OrgRole.OWNER.value)
        await self.repo.add_member(db, owner)

        await db.commit()
        return org

    async def update_organization(
        self,
        db: AsyncSession,
        *,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        data: dict,
    ) -> Organization:
        org = await self.repo.get_org(db, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        await self.require_role(
            db,
            org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value},
        )

        updated = await self.repo.update_org(db, org, data)
        await db.commit()
        return updated

    async def delete_organization(self, db: AsyncSession, *, org_id: uuid.UUID, requester_id: uuid.UUID) -> None:
        org = await self.repo.get_org(db, org_id)
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")

        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value})

        deleted = await self.repo.delete_org(db, org_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Organization not found")
        await db.commit()

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
        requester_member = await self.require_role(
            db,
            org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value},
        )

        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        if role == OrgRole.OWNER.value and requester_member.role != OrgRole.OWNER.value:
            raise HTTPException(status_code=403, detail="Only owner can assign owner role")

        existing = await self.repo.get_member(db, org_id, user_id)
        if existing:
            raise HTTPException(status_code=409, detail="User already a member")

        await self.repo.add_member(db, OrgMember(org_id=org_id, user_id=user_id, role=role))
        await db.commit()

    async def change_role(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value})

        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")

        member = await self.repo.get_member(db, org_id, user_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        if member.role == OrgRole.OWNER.value and role != OrgRole.OWNER.value:
            owner_count = await self._count_owners(db, org_id)
            if owner_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last owner")

        updated = await self.repo.update_role(db, org_id, user_id, role)
        if not updated:
            raise HTTPException(status_code=404, detail="Member not found")
        await db.commit()

    async def remove_member(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID, user_id: uuid.UUID) -> None:
        requester_member = await self.require_role(
            db,
            org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value},
        )

        target_member = await self.repo.get_member(db, org_id, user_id)
        if not target_member:
            raise HTTPException(status_code=404, detail="Member not found")

        if target_member.role == OrgRole.OWNER.value:
            if requester_member.role != OrgRole.OWNER.value:
                raise HTTPException(status_code=403, detail="Only owner can remove an owner")
            owner_count = await self._count_owners(db, org_id)
            if owner_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove the last owner")

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
    ) -> tuple[str, int, str]:
        requester_member = await self.require_role(
            db,
            org_id,
            requester_id,
            allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value},
        )

        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        if role == OrgRole.OWNER.value and requester_member.role != OrgRole.OWNER.value:
            raise HTTPException(status_code=403, detail="Only owner can create owner invites")

        ttl = ttl_seconds or settings.invite_token_ttl_seconds

        token = generate_invite_token()
        h = hash_invite_token(token)

        payload = {
            "org_id": str(org_id),
            "role": role,
            "created_by": str(requester_id),
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        await redis_set_json(invite_key(h), payload, ttl_seconds=ttl)
        await redis_set_add(invites_index_key(str(org_id)), h)

        return token, ttl, h

    async def list_invites(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID) -> list[dict]:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value})

        idx_key = invites_index_key(str(org_id))
        invite_ids = await redis_set_members(idx_key)
        items: list[dict] = []

        for invite_id in invite_ids:
            data = await redis_get_json(invite_key(invite_id))
            if not data or data.get("org_id") != str(org_id):
                await redis_set_remove(idx_key, invite_id)
                continue

            expires_in = await redis_ttl_seconds(invite_key(invite_id))
            if expires_in <= 0:
                await redis_set_remove(idx_key, invite_id)
                continue

            items.append(
                {
                    "invite_id": invite_id,
                    "role": data["role"],
                    "created_by": data["created_by"],
                    "created_at": int(data.get("created_at", 0)),
                    "expires_in": expires_in,
                }
            )

        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items

    async def revoke_invite(self, db: AsyncSession, org_id: uuid.UUID, requester_id: uuid.UUID, invite_id: str) -> None:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value, OrgRole.ADMIN.value})

        key = invite_key(invite_id)
        data = await redis_get_json(key)
        if not data or data.get("org_id") != str(org_id):
            raise HTTPException(status_code=404, detail="Invite not found")

        await redis_del(key)
        await redis_set_remove(invites_index_key(str(org_id)), invite_id)

    async def transfer_ownership(
        self,
        db: AsyncSession,
        org_id: uuid.UUID,
        requester_id: uuid.UUID,
        new_owner_user_id: uuid.UUID,
    ) -> None:
        await self.require_role(db, org_id, requester_id, allowed={OrgRole.OWNER.value})

        if requester_id == new_owner_user_id:
            raise HTTPException(status_code=400, detail="User is already the owner")

        new_owner_member = await self.repo.get_member(db, org_id, new_owner_user_id)
        if not new_owner_member:
            raise HTTPException(status_code=404, detail="Target user is not a member")
        if new_owner_member.role == OrgRole.OWNER.value:
            raise HTTPException(status_code=400, detail="Target user is already an owner")

        promoted = await self.repo.update_role(db, org_id, new_owner_user_id, OrgRole.OWNER.value)
        if not promoted:
            raise HTTPException(status_code=404, detail="Target user is not a member")

        demoted = await self.repo.update_role(db, org_id, requester_id, OrgRole.ADMIN.value)
        if not demoted:
            raise HTTPException(status_code=404, detail="Requester is not a member")

        await db.commit()

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

        org_id = uuid.UUID(data["org_id"])
        role = data["role"]

        if await self.repo.get_member(db, org_id, user_id):
            raise HTTPException(status_code=409, detail="Already a member of this organization")

        await redis_del(key)
        await redis_set_remove(invites_index_key(str(org_id)), h)

        await self.repo.add_member(db, OrgMember(org_id=org_id, user_id=user_id, role=role))
        await db.commit()

        return org_id
