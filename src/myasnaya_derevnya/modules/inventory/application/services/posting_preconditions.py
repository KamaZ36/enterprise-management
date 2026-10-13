from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import Warehouse
from myasnaya_derevnya.modules.inventory.domain.errors import (
    NomenclatureNotFoundError,
    WarehouseInactiveError,
    WarehouseNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)


class PostingPreconditions:
    def __init__(
        self,
        warehouse_repository: WarehouseRepository,
        catalog_api: CatalogAPI,
    ) -> None:
        self._warehouse_repository = warehouse_repository
        self._catalog_api = catalog_api

    async def ensure_ready(
        self, *, warehouse_id: UUID, nomenclature_ids: Iterable[UUID]
    ) -> Warehouse:
        warehouse = await self._warehouse_repository.get_by_id(warehouse_id)
        if warehouse is None:
            raise WarehouseNotFoundError(warehouse_id)
        if not warehouse.is_active:
            raise WarehouseInactiveError(warehouse.id)

        ids = list(nomenclature_ids)
        types = await self._catalog_api.nomenclature_types(ids)

        for nomenclature_id in ids:
            if types.get(nomenclature_id) is None:
                raise NomenclatureNotFoundError(nomenclature_id)

        return warehouse
