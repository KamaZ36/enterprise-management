from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.pos.application.dto import PosReceiptDetail
from myasnaya_derevnya.modules.pos.application.errors import PosReceiptNotFoundError
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_READ
from myasnaya_derevnya.modules.pos.infrastructure.readers.receipt.base import (
    PosReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class GetPosReceiptQuery:
    receipt_id: UUID


class GetPosReceiptInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        business_api: BusinessAPI,
        catalog_api: CatalogAPI,
        receipt_reader: PosReceiptReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._business_api = business_api
        self._catalog_api = catalog_api
        self._receipt_reader = receipt_reader

    async def __call__(self, query: GetPosReceiptQuery) -> PosReceiptDetail:
        user_id = await self._identity_provider.get_current_user_id()

        receipt = await self._receipt_reader.get(query.receipt_id)
        if receipt is None:
            raise PosReceiptNotFoundError(query.receipt_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_RECEIPT_READ,
            org_unit_id=receipt.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        title = (await self._business_api.org_unit_titles({receipt.org_unit_id})).get(
            receipt.org_unit_id
        )

        nomenclature_ids = {
            line.nomenclature_id
            for line in receipt.lines
            if line.nomenclature_id is not None
        }
        names = await self._catalog_api.nomenclature_names(nomenclature_ids)

        return replace(
            receipt,
            org_unit_name=title,
            lines=tuple(
                replace(line, nomenclature_name=names.get(line.nomenclature_id))
                for line in receipt.lines
            ),
        )
