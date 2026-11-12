from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import ShipmentListItem
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.shipment.base import (
    ShipmentReader,
)


@dataclass(frozen=True, slots=True)
class ListShipmentsQuery:
    org_unit_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ShipmentPage:
    items: list[ShipmentListItem]
    total: int
    limit: int
    offset: int


class ListShipmentsInteractor:
    def __init__(
        self,
        shipment_reader: ShipmentReader,
        document_scope: DocumentScope,
    ) -> None:
        self._shipment_reader = shipment_reader
        self._document_scope = document_scope

    async def __call__(self, query: ListShipmentsQuery) -> ShipmentPage:
        org_unit_ids = await self._document_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        items, total = await self._shipment_reader.list(
            org_unit_ids=org_unit_ids,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return ShipmentPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
