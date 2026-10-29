from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.orders.application.dto import Cart
from myasnaya_derevnya.modules.orders.application.services.cart import build_cart
from myasnaya_derevnya.modules.orders.infrastructure.repositories.order.base import (
    OrderRepository,
)


@dataclass(frozen=True, slots=True)
class GetCartQuery:
    org_unit_id: UUID


class GetCartInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_repository: OrderRepository,
        customer_api: CustomerAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_repository = order_repository
        self._customer_api = customer_api

    async def __call__(self, query: GetCartQuery) -> Cart:
        user_id = await self._identity_provider.get_current_user_id()
        customer_id = await self._customer_api.get_customer_id(user_id)

        if customer_id is None:
            raise ForbiddenError()

        order = await self._order_repository.get_open_draft(
            customer_id, query.org_unit_id
        )

        return build_cart(order, query.org_unit_id)
