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
    # Сколько совпадений поиска отдавать в другие модули. Ограничение защищает
    # от разрастания ``IN (...)`` в чужих запросах.
    SEARCH_MATCH_LIMIT = 500

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

    async def nomenclature_ids_matching(self, search: str) -> list[UUID]:
        """Идентификаторы номенклатур, подходящих под поиск по названию/артикулу."""

        return await self._nomenclature_repository.get_ids_by_search(
            search, limit=self.SEARCH_MATCH_LIMIT
        )

    async def nomenclature_id_by_gtin(self, gtin: str) -> UUID | None:
        """Активная номенклатура с таким GTIN, если она есть."""

        return await self._nomenclature_repository.get_id_by_gtin(gtin)

    async def prices_for_point(
        self, org_unit_id: UUID, nomenclature_ids: list[UUID]
    ) -> dict[UUID, int]:
        return await self._get_point_prices_interactor(
            GetPointPricesQuery(
                org_unit_id=org_unit_id, nomenclature_ids=nomenclature_ids
            )
        )
