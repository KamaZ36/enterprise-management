from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.business.domain.entities.org_unit import (
    STOCK_LOCATION_TYPES,
)
from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)


@dataclass(frozen=True, slots=True)
class StockLocation:
    """Складская локация — подразделение, которое хранит запасы."""

    id: UUID
    code: str
    name: str
    is_active: bool


class BusinessAPI:
    def __init__(self, org_unit_repository: OrgUnitRepository) -> None:
        self._org_unit_repository = org_unit_repository

    async def org_unit_ancestors_of(self, org_unit_id: UUID) -> frozenset[UUID]:
        return await self._org_unit_repository.ancestors_of(org_unit_id)

    async def get_root_unit_id(self) -> UUID:
        return await self._org_unit_repository.get_root_id()

    async def org_unit_exists(self, org_unit_id: UUID) -> bool:
        return await self._org_unit_repository.get_by_id(org_unit_id) is not None

    async def org_unit_descendants_of(
        self, org_unit_ids: Iterable[UUID]
    ) -> frozenset[UUID]:
        return await self._org_unit_repository.descendants_of_many(org_unit_ids)

    async def org_unit_titles(self, org_unit_ids: Iterable[UUID]) -> dict[UUID, str]:
        return await self._org_unit_repository.get_titles(org_unit_ids)

    async def stock_location(self, org_unit_id: UUID) -> StockLocation | None:
        """Возвращает локацию, если подразделение существует и хранит запасы."""
        unit = await self._org_unit_repository.get_by_id(org_unit_id)
        if unit is None or unit.type not in STOCK_LOCATION_TYPES:
            return None

        return self._to_location(unit)

    async def stock_locations(self) -> list[StockLocation]:
        units = await self._org_unit_repository.list_by_types(STOCK_LOCATION_TYPES)

        return [self._to_location(unit) for unit in units]

    @staticmethod
    def _to_location(unit) -> StockLocation:
        return StockLocation(
            id=unit.id,
            code=unit.code,
            name=unit.name,
            is_active=unit.is_active,
        )
