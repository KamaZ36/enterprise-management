from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.orders.application.dto import OrderDetail
from myasnaya_derevnya.modules.orders.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.orders.domain.errors import OrderNotFoundError
from myasnaya_derevnya.modules.orders.domain.permissions import READ_ORDERS
from myasnaya_derevnya.modules.orders.infrastructure.readers.order.base import (
    OrderReader,
)


@dataclass(frozen=True, slots=True)
class GetOrderQuery:
    order_id: UUID


class GetOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_reader: OrderReader,
        order_access: OrderAccess,
        catalog_api: CatalogAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_reader = order_reader
        self._order_access = order_access
        self._catalog_api = catalog_api

    async def __call__(self, query: GetOrderQuery) -> OrderDetail:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_reader.get(query.order_id)

        if order is None:
            raise OrderNotFoundError(query.order_id)

        await self._order_access.ensure_can_view(
            user_id=user_id,
            org_unit_id=order.org_unit_id,
            customer_id=order.customer_id,
            permission=READ_ORDERS,
        )

        names = await self._catalog_api.nomenclature_names(
            [line.nomenclature_id for line in order.lines]
        )

        return replace(
            order,
            lines=[
                replace(line, nomenclature_name=names.get(line.nomenclature_id))
                for line in order.lines
            ],
        )
