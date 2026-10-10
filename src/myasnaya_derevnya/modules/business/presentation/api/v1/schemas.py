from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem
from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType


class CreateOrgUnitSchema(BaseModel):
    parent_id: UUID
    type: OrgUnitType
    code: str
    name: str
    address: str | None
    phone_number: str | None


class OrgUnitSchema(BaseModel):
    id: UUID
    parent_id: UUID | None
    type: OrgUnitType
    code: str
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, item: OrgUnitListItem) -> OrgUnitSchema:
        return cls(
            id=item.id,
            parent_id=item.parent_id,
            type=item.type,
            code=item.code,
            name=item.name,
            is_active=item.is_active,
        )
