from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType


class CreateOrgUnitSchema(BaseModel):
    parent_id: UUID
    type: OrgUnitType
    code: str
    name: str
    address: str | None
    phone_number: str | None
