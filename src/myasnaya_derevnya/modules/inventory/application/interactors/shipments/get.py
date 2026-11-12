from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import ShipmentDetail
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.errors import ShipmentNotFoundError
from myasnaya_derevnya.modules.inventory.infrastructure.readers.shipment.base import (
    ShipmentReader,
)


@dataclass(frozen=True, slots=True)
class GetShipmentQuery:
    shipment_id: UUID


class GetShipmentInteractor:
    def __init__(
        self,
        shipment_reader: ShipmentReader,
        catalog_api: CatalogAPI,
        document_scope: DocumentScope,
    ) -> None:
        self._shipment_reader = shipment_reader
        self._catalog_api = catalog_api
        self._document_scope = document_scope

    async def __call__(self, query: GetShipmentQuery) -> ShipmentDetail:
        detail = await self._shipment_reader.get(query.shipment_id)
        if detail is None:
            raise ShipmentNotFoundError(query.shipment_id)

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
