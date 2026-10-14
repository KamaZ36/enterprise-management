from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.base import (
    PriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.base import (
    PriceListBindingRepository,
)


@dataclass(frozen=True, slots=True)
class GetPointPricesQuery:
    org_unit_id: UUID
    nomenclature_ids: list[UUID]


class GetPointPricesInteractor:
    def __init__(
        self,
        binding_repository: PriceListBindingRepository,
        price_repository: PriceRepository,
    ) -> None:
        self._binding_repository = binding_repository
        self._price_repository = price_repository

    async def __call__(self, query: GetPointPricesQuery) -> dict[UUID, int]:
        binding = await self._binding_repository.get_by_org_unit(query.org_unit_id)

        if binding is None:
            return {}

        return await self._price_repository.get_values_by_nomenclatures_and_list(
            nomenclature_ids=query.nomenclature_ids,
            price_list_id=binding.price_list_id,
        )
