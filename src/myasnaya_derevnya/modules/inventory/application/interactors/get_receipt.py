from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.dto import ReceiptDetail
from myasnaya_derevnya.modules.inventory.domain.errors import ReceiptNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_DOCUMENTS
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.base import (
    ReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class GetReceiptQuery:
    receipt_id: UUID


class GetReceiptInteractor:
    """Карточка поступления: строки с названиями номенклатуры."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        receipt_reader: ReceiptReader,
        catalog_api: CatalogAPI,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._receipt_reader = receipt_reader
        self._catalog_api = catalog_api
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, query: GetReceiptQuery) -> ReceiptDetail:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_DOCUMENTS,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        detail = await self._receipt_reader.get(query.receipt_id)
        if detail is None:
            raise ReceiptNotFoundError(query.receipt_id)

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
