from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import NotFoundError


@dataclass(slots=True, eq=False)
class OrgUnitNotFound(NotFoundError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return f"Структурная единица {self.org_unit_id} не найдена."
