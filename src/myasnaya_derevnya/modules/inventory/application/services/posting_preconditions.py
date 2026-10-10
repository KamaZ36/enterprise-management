from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import Warehouse
from myasnaya_derevnya.modules.inventory.domain.errors import (
    NomenclatureNotFoundError,
    WarehouseInactiveError,
    WarehouseNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.services.warehouse_purpose import (
    WarehousePurposePolicy,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)


class PostingPreconditions:
    """Проверки, общие для проведения любого документа."""

    def __init__(
        self,
        warehouse_repository: WarehouseRepository,
        catalog_api: CatalogAPI,
        purpose_policy: WarehousePurposePolicy,
    ) -> None:
        self._warehouse_repository = warehouse_repository
        self._catalog_api = catalog_api
        self._purpose_policy = purpose_policy

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
            type_code = types.get(nomenclature_id)
            if type_code is None:
                raise NomenclatureNotFoundError(nomenclature_id)

            self._purpose_policy.ensure_allowed(
                warehouse=warehouse,
                nomenclature_id=nomenclature_id,
                nomenclature_type_code=type_code,
            )

        return warehouse
