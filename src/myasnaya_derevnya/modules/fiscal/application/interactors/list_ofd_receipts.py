from dataclasses import dataclass, replace
from datetime import datetime

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.fiscal.application.dto import OfdReceiptListPage
from myasnaya_derevnya.modules.fiscal.domain.permissions import (
    CASH_REGISTER_RECEIPT_READ,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.base import (
    OfdReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListOfdReceiptsQuery:
    status: str | None = None
    reg_number: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = 50
    offset: int = 0


class ListOfdReceiptsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        receipt_reader: OfdReceiptReader,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._receipt_reader = receipt_reader
        self._business_api = business_api

    async def __call__(self, query: ListOfdReceiptsQuery) -> OfdReceiptListPage:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=CASH_REGISTER_RECEIPT_READ
        )
        if scope.is_empty():
            raise ForbiddenError()

        items, total = await self._receipt_reader.list(
            status=query.status,
            reg_number=query.reg_number,
            date_from=query.date_from,
            date_to=query.date_to,
            org_unit_ids=None if scope.is_company_wide else scope.org_unit_ids,
            limit=query.limit,
            offset=query.offset,
        )

        org_unit_ids = {
            item.org_unit_id for item in items if item.org_unit_id is not None
        }
        titles = await self._business_api.org_unit_titles(org_unit_ids)

        return OfdReceiptListPage(
            items=tuple(
                replace(
                    item,
                    org_unit_name=(
                        titles.get(item.org_unit_id)
                        if item.org_unit_id is not None
                        else None
                    ),
                )
                for item in items
            ),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
