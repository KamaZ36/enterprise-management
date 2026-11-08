from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import OpeningBalanceDetail
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    OpeningBalanceNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.opening_balance.base import (
    OpeningBalanceReader,
)


@dataclass(frozen=True, slots=True)
class GetOpeningBalanceQuery:
    opening_balance_id: UUID


class GetOpeningBalanceInteractor:
    def __init__(
        self,
        opening_balance_reader: OpeningBalanceReader,
        catalog_api: CatalogAPI,
        document_scope: DocumentScope,
    ) -> None:
        self._opening_balance_reader = opening_balance_reader
        self._catalog_api = catalog_api
        self._document_scope = document_scope

    async def __call__(self, query: GetOpeningBalanceQuery) -> OpeningBalanceDetail:
        detail = await self._opening_balance_reader.get(query.opening_balance_id)
        if detail is None:
            raise OpeningBalanceNotFoundError(query.opening_balance_id)

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
