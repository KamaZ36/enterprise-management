from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.pos.application.dto import PosReceiptListPage
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_READ
from myasnaya_derevnya.modules.pos.infrastructure.readers.receipt.base import (
    PosReceiptReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListPosReceiptsQuery:
    source_id: UUID | None = None
    status: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    org_unit_id: UUID | None = None
    limit: int = 50
    offset: int = 0


class ListPosReceiptsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        business_api: BusinessAPI,
        receipt_reader: PosReceiptReader,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._business_api = business_api
        self._receipt_reader = receipt_reader

    async def __call__(self, query: ListPosReceiptsQuery) -> PosReceiptListPage:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=POS_RECEIPT_READ
        )
        if scope.is_empty():
            raise ForbiddenError()

        org_unit_ids = scope.narrow(query.org_unit_id)
        if org_unit_ids == frozenset():
            return PosReceiptListPage(
                items=(),
                total=0,
                limit=query.limit,
                offset=query.offset,
            )

        items, total = await self._receipt_reader.list(
            source_id=query.source_id,
            status=query.status,
            date_from=query.date_from,
            date_to=query.date_to,
            org_unit_ids=org_unit_ids,
            limit=query.limit,
            offset=query.offset,
        )

        titles = await self._business_api.org_unit_titles(
            {item.org_unit_id for item in items}
        )

        return PosReceiptListPage(
            items=tuple(
                replace(item, org_unit_name=titles.get(item.org_unit_id))
                for item in items
            ),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )
