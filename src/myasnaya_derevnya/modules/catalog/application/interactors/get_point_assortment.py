from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.catalog.application.dto import AssortmentItem
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.price_lists import (
    SQLAlchemyPriceListsReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.base import (
    PriceListBindingRepository,
)


@dataclass(frozen=True, slots=True)
class GetPointAssortmentQuery:
    org_unit_id: UUID


class GetPointAssortmentInteractor:
    def __init__(
        self,
        binding_repository: PriceListBindingRepository,
        reader: SQLAlchemyPriceListsReader,
    ) -> None:
        self._binding_repository = binding_repository
        self._reader = reader

    async def __call__(self, query: GetPointAssortmentQuery) -> list[AssortmentItem]:
        binding = await self._binding_repository.get_by_org_unit(query.org_unit_id)
        if binding is None:
            return []

        return await self._reader.list_assortment(binding.price_list_id)
