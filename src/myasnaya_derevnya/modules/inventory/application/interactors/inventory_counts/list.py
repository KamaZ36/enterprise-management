from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    InventoryCountListItem,
)
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.inventory_count.base import (
    InventoryCountReader,
)


@dataclass(frozen=True, slots=True)
class ListInventoryCountsQuery:
    org_unit_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class InventoryCountPage:
    items: list[InventoryCountListItem]
    total: int
    limit: int
    offset: int


class ListInventoryCountsInteractor:
    def __init__(
        self,
        inventory_count_reader: InventoryCountReader,
        document_scope: DocumentScope,
    ) -> None:
        self._inventory_count_reader = inventory_count_reader
        self._document_scope = document_scope

    async def __call__(self, query: ListInventoryCountsQuery) -> InventoryCountPage:
        org_unit_ids = await self._document_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        items, total = await self._inventory_count_reader.list(
            org_unit_ids=org_unit_ids,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return InventoryCountPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
