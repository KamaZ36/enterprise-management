from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType


@dataclass(frozen=True, slots=True)
class OrgUnitListItem:
    id: UUID
    parent_id: UUID | None
    type: OrgUnitType
    code: str
    name: str
    is_active: bool
    address: str | None
    phone_number: str | None
