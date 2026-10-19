from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import InventoryCountDetail
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    InventoryCountNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.inventory_count.base import (
    InventoryCountReader,
)


@dataclass(frozen=True, slots=True)
class GetInventoryCountQuery:
    inventory_count_id: UUID


class GetInventoryCountInteractor:
    def __init__(
        self,
        inventory_count_reader: InventoryCountReader,
        catalog_api: CatalogAPI,
        document_scope: DocumentScope,
    ) -> None:
        self._inventory_count_reader = inventory_count_reader
        self._catalog_api = catalog_api
        self._document_scope = document_scope

    async def __call__(self, query: GetInventoryCountQuery) -> InventoryCountDetail:
        detail = await self._inventory_count_reader.get(query.inventory_count_id)
        if detail is None:
            raise InventoryCountNotFoundError(query.inventory_count_id)

        await self._document_scope.ensure_can_read([detail.org_unit_id])

        names = await self._catalog_api.nomenclature_names(
            {line.nomenclature_id for line in detail.lines}
        )

        return replace(
            detail,
            lines=[
                replace(line, nomenclature_name=names.get(line.nomenclature_id))
                for line in detail.lines
            ],
        )
