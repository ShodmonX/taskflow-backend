from pydantic import BaseModel, Field
from uuid import UUID

class OrgCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)

class OrgResponse(BaseModel):
    id: UUID
    name: str
    created_by: UUID

class OrgListResponse(BaseModel):
    items: list[OrgResponse]

class MemberAddRequest(BaseModel):
    user_id: UUID
    role: str = "MEMBER"

class MemberResponse(BaseModel):
    user_id: UUID
    role: str

class MemberListResponse(BaseModel):
    items: list[MemberResponse]

class MemberRoleUpdateRequest(BaseModel):
    role: str

class InviteCreateRequest(BaseModel):
    role: str = "MEMBER"
    ttl_seconds: int | None = Field(default=None, ge=60, le=60 * 60 * 24 * 7)

class InviteCreateResponse(BaseModel):
    invite_token: str
    org_id: UUID
    role: str
    expires_in: int

class JoinByInviteRequest(BaseModel):
    invite_token: str