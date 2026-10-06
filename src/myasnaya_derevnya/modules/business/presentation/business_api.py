from uuid import UUID

from myasnaya_derevnya.modules.business.infrastructure.repositories.org_unit_repository.base import (
    OrgUnitRepository,
)


class BusinessAPI:
    def __init__(self, org_unit_repository: OrgUnitRepository) -> None:
        self._org_unit_repository = org_unit_repository

    async def org_unit_ancestors_of(self, org_unit_id: UUID) -> frozenset[UUID]:
        return await self._org_unit_repository.ancestors_of(org_unit_id)
