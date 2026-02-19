from pydantic import BaseModel, Field
from uuid import UUID

ALLOWED_STATUSES = {"TODO", "IN_PROGRESS", "DONE"}

class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str = Field(default="TODO")

class TaskResponse(BaseModel):
    id: UUID
    org_id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: str
    created_by: UUID | None

class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    limit: int
    offset: int
    total: int
