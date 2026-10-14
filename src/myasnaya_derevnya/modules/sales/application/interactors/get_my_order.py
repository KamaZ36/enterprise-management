from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.sales.application.dto import OrderDetail
from myasnaya_derevnya.modules.sales.domain.errors import OrderNotFoundError
from myasnaya_derevnya.modules.sales.infrastructure.readers.order.base import (
    OrderReader,
)


@dataclass(frozen=True, slots=True)
class GetMyOrderQuery:
    order_id: UUID


class GetMyOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_reader: OrderReader,
        customer_api: CustomerAPI,
        catalog_api: CatalogAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_reader = order_reader
        self._customer_api = customer_api
        self._catalog_api = catalog_api

    async def __call__(self, query: GetMyOrderQuery) -> OrderDetail:
        user_id = await self._identity_provider.get_current_user_id()
        customer_id = await self._customer_api.get_customer_id(user_id)
        order = await self._order_reader.get(query.order_id)

        if order is None or customer_id is None or order.customer_id != customer_id:
            raise OrderNotFoundError(query.order_id)

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
