from pydantic import BaseModel, Field
from uuid import UUID


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: str | None
    created_by: UUID | None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
