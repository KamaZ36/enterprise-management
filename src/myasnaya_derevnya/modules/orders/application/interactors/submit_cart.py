import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.orders.domain.errors import (
    EmptyCartError,
    NotSoldAtPointError,
)
from myasnaya_derevnya.modules.orders.infrastructure.repositories.order.base import (
    OrderRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SubmitCartCommand:
    org_unit_id: UUID


class SubmitCartInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_repository: OrderRepository,
        catalog_api: CatalogAPI,
        customer_api: CustomerAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_repository = order_repository
        self._catalog_api = catalog_api
        self._customer_api = customer_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: SubmitCartCommand) -> UUID:
        user_id = await self._identity_provider.get_current_user_id()
        customer_id = await self._customer_api.get_customer_id(user_id)

        if customer_id is None:
            raise ForbiddenError()

        order = await self._order_repository.get_open_draft(
            customer_id, command.org_unit_id
        )

        if order is None or not order.lines:
            raise EmptyCartError()

        prices = await self._catalog_api.prices_for_point(
            command.org_unit_id, [line.nomenclature_id for line in order.lines]
        )

        resolved: list[tuple[UUID, Decimal, int]] = []

        for line in order.lines:
            price = prices.get(line.nomenclature_id)

            if price is None:
                raise NotSoldAtPointError(line.nomenclature_id)

            resolved.append((line.nomenclature_id, line.quantity, price))

        order.revise(resolved, comment=order.comment)
        order.assign_number(
            await self._order_repository.next_number(
                order.org_unit_id, order.created_at.date()
            )
        )
        order.submit()

        await self._order_repository.save(order)
        await self._transaction_manager.commit()

        logger.info(
            "Корзина отправлена в заказ",
            extra={
                "order_id": str(order.id),
                "org_unit_id": str(order.org_unit_id),
            },
        )

        return order.id
