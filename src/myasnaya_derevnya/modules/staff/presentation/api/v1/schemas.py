from uuid import UUID

from pydantic import BaseModel, Field


class AssignRoleCommandSchema(BaseModel):
    role_id: UUID
    target_location_id: UUID | None = Field(default=None)
