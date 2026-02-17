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
