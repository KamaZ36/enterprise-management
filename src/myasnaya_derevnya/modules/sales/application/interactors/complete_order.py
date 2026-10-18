import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
    SaleLine,
)
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.sales.domain.errors import OrderNotFoundError
from myasnaya_derevnya.modules.sales.domain.permissions import UPDATE_ORDER
from myasnaya_derevnya.modules.sales.domain.value_objects.order_status import (
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.payment import PaymentMethod
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CompleteOrderCommand:
    order_id: UUID


class CompleteOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_repository: OrderRepository,
        order_access: OrderAccess,
        inventory_api: InventoryAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_repository = order_repository
        self._order_access = order_access
        self._inventory_api = inventory_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CompleteOrderCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)
        if order is None:
            raise OrderNotFoundError(command.order_id)

        await self._order_access.ensure_is_staff(
            user_id=user_id, order=order, permission=UPDATE_ORDER
        )

        order.set_status(OrderStatus.COMPLETED)

        if order.payment_method in (
            PaymentMethod.ON_PICKUP,
            PaymentMethod.ON_DELIVERY,
        ):
            order.mark_paid()

        await self._write_off_stock(order=order, user_id=user_id)

        await self._order_repository.save(order)
        await self._transaction_manager.commit()

        logger.info("Заказ выполнен", extra={"order_id": str(order.id)})

    async def _write_off_stock(self, *, order: Order, user_id: UUID) -> None:
        lines = order.lines
        if not lines:
            return

        location = await self._inventory_api.get_location(order.org_unit_id)
        if location is None:
            return

        costs = await self._inventory_api.post_sale(
            document_id=order.id,
            org_unit_id=location.id,
            occurred_at=order.completed_at or get_datetime_utc(),
            lines=[
                SaleLine(nomenclature_id=line.nomenclature_id, quantity=line.quantity)
                for line in lines
            ],
            posted_by=user_id,
        )

        order.apply_costs(list(costs))
