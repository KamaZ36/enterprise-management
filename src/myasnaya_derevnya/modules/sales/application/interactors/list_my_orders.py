from dataclasses import dataclass
from datetime import date

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.sales.application.dto import OrderListItem
from myasnaya_derevnya.modules.sales.infrastructure.readers.order.base import (
    OrderReader,
)


@dataclass(frozen=True, slots=True)
class ListMyOrdersQuery:
    statuses: list[str] | None = None
    day: date | None = None
    limit: int = 50
    offset: int = 0


class ListMyOrdersInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_reader: OrderReader,
        customer_api: CustomerAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_reader = order_reader
        self._customer_api = customer_api

    async def __call__(
        self, query: ListMyOrdersQuery
    ) -> tuple[list[OrderListItem], int]:
        user_id = await self._identity_provider.get_current_user_id()
        customer_id = await self._customer_api.get_customer_id(user_id)

        if customer_id is None:
            raise ForbiddenError()

        return await self._order_reader.list(
            customer_id=customer_id,
            statuses=query.statuses,
            day=query.day,
            limit=query.limit,
            offset=query.offset,
            exclude_drafts=True,
        )
