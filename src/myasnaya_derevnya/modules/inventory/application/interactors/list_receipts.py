from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.dto import ReceiptListItem
from myasnaya_derevnya.modules.inventory.domain.permissions import READ_DOCUMENTS
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.base import (
    ReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListReceiptsQuery:
    warehouse_id: UUID | None = None
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ReceiptPage:
    items: list[ReceiptListItem]
    total: int
    limit: int
    offset: int


class ListReceiptsInteractor:
    """Журнал поступлений: что и когда привозили."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        receipt_reader: ReceiptReader,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._receipt_reader = receipt_reader
        self._business_api = business_api
        self._staff_api = staff_api

    async def __call__(self, query: ListReceiptsQuery) -> ReceiptPage:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=READ_DOCUMENTS,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        items, total = await self._receipt_reader.list(
            warehouse_id=query.warehouse_id,
            limit=query.limit,
            offset=query.offset,
        )

        return ReceiptPage(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
