from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import ReceiptListItem
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.base import (
    ReceiptReader,
)


@dataclass(frozen=True, slots=True)
class ListReceiptsQuery:
    org_unit_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ReceiptPage:
    items: list[ReceiptListItem]
    total: int
    limit: int
    offset: int


class ListReceiptsInteractor:
    def __init__(
        self,
        receipt_reader: ReceiptReader,
        document_scope: DocumentScope,
    ) -> None:
        self._receipt_reader = receipt_reader
        self._document_scope = document_scope

    async def __call__(self, query: ListReceiptsQuery) -> ReceiptPage:
        org_unit_ids = await self._document_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        items, total = await self._receipt_reader.list(
            org_unit_ids=org_unit_ids,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return ReceiptPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
