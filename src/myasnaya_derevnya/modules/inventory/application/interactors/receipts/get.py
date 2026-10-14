from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import ReceiptDetail
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    ReceiptNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.base import (
    ReceiptReader,
)


@dataclass(frozen=True, slots=True)
class GetReceiptQuery:
    receipt_id: UUID


class GetReceiptInteractor:
    def __init__(
        self,
        receipt_reader: ReceiptReader,
        catalog_api: CatalogAPI,
        document_scope: DocumentScope,
    ) -> None:
        self._receipt_reader = receipt_reader
        self._catalog_api = catalog_api
        self._document_scope = document_scope

    async def __call__(self, query: GetReceiptQuery) -> ReceiptDetail:
        detail = await self._receipt_reader.get(query.receipt_id)
        if detail is None:
            raise ReceiptNotFoundError(query.receipt_id)

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
