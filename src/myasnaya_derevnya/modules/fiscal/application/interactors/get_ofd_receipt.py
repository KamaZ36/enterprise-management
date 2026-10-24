from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.fiscal.application.dto import OfdReceiptDetail
from myasnaya_derevnya.modules.fiscal.application.errors import OfdReceiptNotFound
from myasnaya_derevnya.modules.fiscal.domain.permissions import (
    CASH_REGISTER_RECEIPT_READ,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.base import (
    OfdReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class GetOfdReceiptQuery:
    receipt_id: UUID


class GetOfdReceiptInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        receipt_reader: OfdReceiptReader,
        business_api: BusinessAPI,
        catalog_api: CatalogAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._receipt_reader = receipt_reader
        self._business_api = business_api
        self._catalog_api = catalog_api

    async def __call__(self, query: GetOfdReceiptQuery) -> OfdReceiptDetail:
        user_id = await self._identity_provider.get_current_user_id()
        detail = await self._receipt_reader.get(query.receipt_id)
        if detail is None:
            raise OfdReceiptNotFound(query.receipt_id)

        await self._ensure_access(user_id=user_id, detail=detail)

        org_unit_name = None
        if detail.org_unit_id is not None:
            titles = await self._business_api.org_unit_titles({detail.org_unit_id})
            org_unit_name = titles.get(detail.org_unit_id)

        nomenclature_ids = {
            line.nomenclature_id
            for line in detail.lines
            if line.nomenclature_id is not None
        }
        names = await self._catalog_api.nomenclature_names(nomenclature_ids)

        return replace(
            detail,
            org_unit_name=org_unit_name,
            lines=tuple(
                replace(
                    line,
                    nomenclature_name=(
                        names.get(line.nomenclature_id)
                        if line.nomenclature_id is not None
                        else None
                    ),
                )
                for line in detail.lines
            ),
        )

    async def _ensure_access(self, *, user_id: UUID, detail: OfdReceiptDetail) -> None:
        if detail.org_unit_id is not None:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=CASH_REGISTER_RECEIPT_READ,
                org_unit_id=detail.org_unit_id,
            )
        else:
            allowed = await self._staff_api.can_anywhere(
                user_id=user_id, permission=CASH_REGISTER_RECEIPT_READ
            )

        if not allowed:
            raise ForbiddenError()
