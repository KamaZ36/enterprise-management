from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.business.presentation.business_api import (
    BusinessAPI,
    StockLocation,
)
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.domain.errors import (
    LocationInactiveError,
    LocationNotFoundError,
    NomenclatureNotFoundError,
)


class PostingPreconditions:
    def __init__(
        self,
        business_api: BusinessAPI,
        catalog_api: CatalogAPI,
    ) -> None:
        self._business_api = business_api
        self._catalog_api = catalog_api

    async def ensure_ready(
        self, *, org_unit_id: UUID, nomenclature_ids: Iterable[UUID]
    ) -> StockLocation:
        location = await self._business_api.stock_location(org_unit_id)
        if location is None:
            raise LocationNotFoundError(org_unit_id)
        if not location.is_active:
            raise LocationInactiveError(location.id)

        ids = list(nomenclature_ids)
        names = await self._catalog_api.nomenclature_names(ids)

        for nomenclature_id in ids:
            if names.get(nomenclature_id) is None:
                raise NomenclatureNotFoundError(nomenclature_id)

        return location
