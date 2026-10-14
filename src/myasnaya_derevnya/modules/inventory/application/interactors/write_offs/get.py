from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import WriteOffDetail
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import WriteOffNotFoundError
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.base import (
    WriteOffReader,
)


@dataclass(frozen=True, slots=True)
class GetWriteOffQuery:
    write_off_id: UUID


class GetWriteOffInteractor:
    def __init__(
        self,
        write_off_reader: WriteOffReader,
        catalog_api: CatalogAPI,
        document_scope: DocumentScope,
    ) -> None:
        self._write_off_reader = write_off_reader
        self._catalog_api = catalog_api
        self._document_scope = document_scope

    async def __call__(self, query: GetWriteOffQuery) -> WriteOffDetail:
        detail = await self._write_off_reader.get(query.write_off_id)
        if detail is None:
            raise WriteOffNotFoundError(query.write_off_id)

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
