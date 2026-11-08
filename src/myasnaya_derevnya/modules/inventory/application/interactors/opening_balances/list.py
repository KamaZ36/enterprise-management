from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.inventory.application.dto import (
    OpeningBalanceListItem,
)
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.opening_balance.base import (
    OpeningBalanceReader,
)


@dataclass(frozen=True, slots=True)
class ListOpeningBalancesQuery:
    org_unit_id: UUID | None = None
    search: str | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class OpeningBalancePage:
    items: list[OpeningBalanceListItem]
    total: int
    limit: int
    offset: int


class ListOpeningBalancesInteractor:
    def __init__(
        self,
        opening_balance_reader: OpeningBalanceReader,
        document_scope: DocumentScope,
    ) -> None:
        self._opening_balance_reader = opening_balance_reader
        self._document_scope = document_scope

    async def __call__(
        self, query: ListOpeningBalancesQuery
    ) -> OpeningBalancePage:
        org_unit_ids = await self._document_scope.visible_org_unit_ids(
            query.org_unit_id
        )

        items, total = await self._opening_balance_reader.list(
            org_unit_ids=org_unit_ids,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
        )

        return OpeningBalancePage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
