from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import TransferListItem
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.transfer.base import (
    TransferReader,
)


@dataclass(frozen=True, slots=True)
class ListTransfersQuery:
    org_unit_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class TransferPage:
    items: list[TransferListItem]
    total: int
    limit: int
    offset: int


class ListTransfersInteractor:
    def __init__(
        self,
        transfer_reader: TransferReader,
        document_scope: DocumentScope,
    ) -> None:
        self._transfer_reader = transfer_reader
        self._document_scope = document_scope

    async def __call__(self, query: ListTransfersQuery) -> TransferPage:
        org_unit_ids = await self._document_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        items, total = await self._transfer_reader.list(
            org_unit_ids=org_unit_ids,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return TransferPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
