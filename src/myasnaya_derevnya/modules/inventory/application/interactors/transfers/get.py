from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import TransferDetail
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import TransferNotFoundError
from myasnaya_derevnya.modules.inventory.infrastructure.readers.transfer.base import (
    TransferReader,
)


@dataclass(frozen=True, slots=True)
class GetTransferQuery:
    transfer_id: UUID


class GetTransferInteractor:
    def __init__(
        self,
        transfer_reader: TransferReader,
        catalog_api: CatalogAPI,
        document_scope: DocumentScope,
    ) -> None:
        self._transfer_reader = transfer_reader
        self._catalog_api = catalog_api
        self._document_scope = document_scope

    async def __call__(self, query: GetTransferQuery) -> TransferDetail:
        detail = await self._transfer_reader.get(query.transfer_id)
        if detail is None:
            raise TransferNotFoundError(query.transfer_id)

        await self._document_scope.ensure_can_read(
            [detail.from_org_unit_id, detail.to_org_unit_id]
        )

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
