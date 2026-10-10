from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType


@dataclass(frozen=True, slots=True)
class OrgUnitListItem:
    """Строка организационной структуры: плоский список со ссылкой на родителя."""

    id: UUID
    parent_id: UUID | None
    type: OrgUnitType
    code: str
    name: str
    is_active: bool
