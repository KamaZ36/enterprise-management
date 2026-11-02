from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.catalog.infrastructure.readers.stop_list.base import (
    StopListReader,
)
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
    """Цены позиций, которые можно продать в точке.

    Учитывает не только прайс-лист, но и стоп-лист: остановленный товар
    не должен попасть в заказ, даже если цена у него есть.
    """

    def __init__(
        self,
        binding_repository: PriceListBindingRepository,
        price_repository: PriceRepository,
        stop_list_reader: StopListReader,
    ) -> None:
        self._binding_repository = binding_repository
        self._price_repository = price_repository
        self._stop_list_reader = stop_list_reader

    async def __call__(self, query: GetPointPricesQuery) -> dict[UUID, int]:
        binding = await self._binding_repository.get_by_org_unit(query.org_unit_id)

        if binding is None:
            return {}

        prices = await self._price_repository.get_values_by_nomenclatures_and_list(
            nomenclature_ids=query.nomenclature_ids,
            price_list_id=binding.price_list_id,
        )
        if not prices:
            return {}

        stopped = await self._stop_list_reader.stopped_nomenclature_ids(
            query.org_unit_id, prices.keys()
        )

        return {
            nomenclature_id: value
            for nomenclature_id, value in prices.items()
            if nomenclature_id not in stopped
        }
