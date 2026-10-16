from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import WriteOffListItem
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.base import (
    WriteOffReader,
)


@dataclass(frozen=True, slots=True)
class ListWriteOffsQuery:
    org_unit_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class WriteOffPage:
    items: list[WriteOffListItem]
    total: int
    limit: int
    offset: int


class ListWriteOffsInteractor:
    def __init__(
        self,
        write_off_reader: WriteOffReader,
        document_scope: DocumentScope,
    ) -> None:
        self._write_off_reader = write_off_reader
        self._document_scope = document_scope

    async def __call__(self, query: ListWriteOffsQuery) -> WriteOffPage:
        org_unit_ids = await self._document_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        items, total = await self._write_off_reader.list(
            org_unit_ids=org_unit_ids,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return WriteOffPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
