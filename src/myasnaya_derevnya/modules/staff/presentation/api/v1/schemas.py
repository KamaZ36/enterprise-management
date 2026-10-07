from uuid import UUID

from pydantic import BaseModel


class AssignRoleCommandSchema(BaseModel):
    role_id: UUID
    org_unit_id: UUID
    include_descendants: bool
