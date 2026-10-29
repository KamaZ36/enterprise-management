from dataclasses import dataclass
from datetime import date
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.orders.application.dto import OrderListItem
from myasnaya_derevnya.modules.orders.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.orders.domain.permissions import READ_ORDERS
from myasnaya_derevnya.modules.orders.infrastructure.readers.order.base import (
    OrderReader,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ListOrdersQuery:
    org_unit_id: UUID | None = None
    customer_id: UUID | None = None
    statuses: list[str] | None = None
    day: date | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


class ListOrdersInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_reader: OrderReader,
        order_access: OrderAccess,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_reader = order_reader
        self._order_access = order_access
        self._staff_api = staff_api

    async def __call__(self, query: ListOrdersQuery) -> tuple[list[OrderListItem], int]:
        user_id = await self._identity_provider.get_current_user_id()

        scope = await self._staff_api.scope_for(user_id=user_id, permission=READ_ORDERS)

        if scope.is_empty():
            raise ForbiddenError()

        org_unit_ids = scope.narrow(query.org_unit_id)

        if org_unit_ids is not None and not org_unit_ids:
            raise ForbiddenError()

        return await self._order_reader.list(
            org_unit_ids=None if org_unit_ids is None else sorted(org_unit_ids),
            statuses=query.statuses,
            day=query.day,
            customer_id=query.customer_id,
            search=query.search,
            limit=query.limit,
            offset=query.offset,
            exclude_drafts=True,
        )
