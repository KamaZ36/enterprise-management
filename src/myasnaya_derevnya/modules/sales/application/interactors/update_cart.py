from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.sales.application.dto import Cart
from myasnaya_derevnya.modules.sales.application.services.cart import (
    PAYMENT_METHOD_BY_FULFILLMENT,
    build_cart,
)
from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.sales.domain.errors import NotSoldAtPointError
from myasnaya_derevnya.modules.sales.domain.value_objects.fulfillment import (
    FulfillmentType,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)


@dataclass(frozen=True, slots=True)
class CartLineCommand:
    nomenclature_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class UpdateCartCommand:
    org_unit_id: UUID
    fulfillment_type: FulfillmentType
    lines: tuple[CartLineCommand, ...] = field(default_factory=tuple)
    comment: str | None = None


class UpdateCartInteractor:
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

    async def __call__(self, command: UpdateCartCommand) -> Cart:
        user_id = await self._identity_provider.get_current_user_id()
        customer_id = await self._customer_api.get_customer_id(user_id)

        if customer_id is None:
            raise ForbiddenError()

        order = await self._order_repository.get_open_draft(
            customer_id, command.org_unit_id
        )
        is_new = order is None

        if order is None:
            order = Order.create(
                org_unit_id=command.org_unit_id,
                channel=OrderChannel.SITE,
                created_by=user_id,
                customer_id=customer_id,
            )

        lines = _merge_lines(command.lines)

        prices = await self._catalog_api.prices_for_point(
            command.org_unit_id, [line.nomenclature_id for line in lines]
        )

        resolved: list[tuple[UUID, Decimal, int]] = []

        for line in lines:
            price = prices.get(line.nomenclature_id)

            if price is None:
                raise NotSoldAtPointError(line.nomenclature_id)

            resolved.append((line.nomenclature_id, line.quantity, price))

        order.revise(resolved, comment=command.comment)
        order.set_fulfillment(
            command.fulfillment_type,
            PAYMENT_METHOD_BY_FULFILLMENT[command.fulfillment_type],
        )

        if is_new:
            await self._order_repository.add(order)
        else:
            await self._order_repository.save(order)

        await self._transaction_manager.commit()

        return build_cart(order, command.org_unit_id)


def _merge_lines(lines: tuple[CartLineCommand, ...]) -> list[CartLineCommand]:
    merged: dict[UUID, Decimal] = {}

    for line in lines:
        merged[line.nomenclature_id] = (
            merged.get(line.nomenclature_id, Decimal(0)) + line.quantity
        )

    return [
        CartLineCommand(nomenclature_id=nomenclature_id, quantity=quantity)
        for nomenclature_id, quantity in merged.items()
    ]
