from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.business.application.dto import (
    CafeOrgUnitListItem,
    OrgUnitListItem,
)
from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType


class CreateOrgUnitSchema(BaseModel):
    parent_id: UUID
    type: OrgUnitType
    code: str
    name: str
    address: str | None
    phone_number: str | None


class UpdateOrgUnitSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    address: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None


class OrgUnitSchema(BaseModel):
    id: UUID
    parent_id: UUID | None
    type: OrgUnitType
    code: str
    name: str
    is_active: bool
    address: str | None
    phone_number: str | None

    @classmethod
    def from_dto(cls, item: OrgUnitListItem) -> OrgUnitSchema:
        return cls(
            id=item.id,
            parent_id=item.parent_id,
            type=item.type,
            code=item.code,
            name=item.name,
            is_active=item.is_active,
            address=item.address,
            phone_number=item.phone_number,
        )


class CafeOrgUnitSchema(BaseModel):
    id: UUID
    type: OrgUnitType
    code: str
    name: str
    address: str | None
    phone_number: str | None

    @classmethod
    def from_dto(cls, item: CafeOrgUnitListItem) -> CafeOrgUnitSchema:
        return cls(
            id=item.id,
            type=item.type,
            code=item.code,
            name=item.name,
            address=item.address,
            phone_number=item.phone_number,
        )
