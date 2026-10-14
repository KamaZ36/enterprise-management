from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.catalog.application.interactors.get_point_prices import (
    GetPointPricesInteractor,
    GetPointPricesQuery,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)


class CatalogAPI:
    # цены для точки нужны заказу и витрине
    def __init__(
        self,
        get_point_prices_interactor: GetPointPricesInteractor,
        nomenclature_repository: NomenclatureRepository,
    ) -> None:
        self._get_point_prices_interactor = get_point_prices_interactor
        self._nomenclature_repository = nomenclature_repository

    async def nomenclature_names(
        self, nomenclature_ids: Iterable[UUID]
    ) -> dict[UUID, str]:
        return await self._nomenclature_repository.get_names(set(nomenclature_ids))

    async def nomenclature_types(
        self, nomenclature_ids: Iterable[UUID]
    ) -> dict[UUID, str]:
        return await self._nomenclature_repository.get_types(set(nomenclature_ids))

    async def prices_for_point(
        self, org_unit_id: UUID, nomenclature_ids: list[UUID]
    ) -> dict[UUID, int]:
        return await self._get_point_prices_interactor(
            GetPointPricesQuery(
                org_unit_id=org_unit_id, nomenclature_ids=nomenclature_ids
            )
        )
