from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI
from myasnaya_derevnya.modules.sales.domain.entities.order import (
    Order,
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.domain.errors import NotSoldAtPointError
from myasnaya_derevnya.modules.sales.domain.permissions import CREATE_ORDER
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class OrderLineCommand:
    nomenclature_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class CreateOrderCommand:
    org_unit_id: UUID
    channel: OrderChannel
    customer_id: UUID | None = None
    planned_at: datetime | None = None
    comment: str | None = None
    lines: tuple[OrderLineCommand, ...] = field(default_factory=tuple)


class CreateOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_repository: OrderRepository,
        catalog_api: CatalogAPI,
        customer_api: CustomerAPI,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_repository = order_repository
        self._catalog_api = catalog_api
        self._customer_api = customer_api
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateOrderCommand) -> UUID:
        user_id = await self._identity_provider.get_current_user_id()

        customer_id = await self._resolve_customer(user_id=user_id, command=command)

        contact_phone = (
            await self._customer_api.contact_phone_by_customer_id(customer_id)
            if customer_id is not None
            else None
        )

        prices = await self._catalog_api.prices_for_point(
            command.org_unit_id,
            [line.nomenclature_id for line in command.lines],
        )

        order = Order.create(
            org_unit_id=command.org_unit_id,
            channel=command.channel,
            created_by=user_id,
            customer_id=customer_id,
            planned_at=command.planned_at,
            comment=command.comment,
            contact_phone=contact_phone,
        )

        for line in command.lines:
            price = prices.get(line.nomenclature_id)

            if price is None:
                raise NotSoldAtPointError(line.nomenclature_id)

            order.add_line(
                nomenclature_id=line.nomenclature_id,
                quantity=line.quantity,
                unit_price=price,
            )

        await self._order_repository.add(order)
        await self._transaction_manager.commit()

        return order.id

    async def _resolve_customer(
        self, *, user_id: UUID, command: CreateOrderCommand
    ) -> UUID | None:
        is_staff = await self._staff_api.can(
            user_id=user_id,
            permission=CREATE_ORDER,
            org_unit_id=command.org_unit_id,
        )

        if is_staff:
            return command.customer_id

        own_customer_id = await self._customer_api.get_customer_id(user_id)

        if own_customer_id is None:
            raise ForbiddenError()

        if command.channel is not OrderChannel.SITE:
            raise ForbiddenError()

        if command.customer_id is not None and command.customer_id != own_customer_id:
            raise ForbiddenError()

        return own_customer_id
