import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.orders.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.orders.domain.errors import (
    OrderNotFoundError,
    OrderNotPaidError,
)
from myasnaya_derevnya.modules.orders.domain.permissions import UPDATE_ORDER
from myasnaya_derevnya.modules.orders.domain.value_objects.order_status import (
    OrderStatus,
)
from myasnaya_derevnya.modules.orders.domain.value_objects.payment import PaymentMethod
from myasnaya_derevnya.modules.orders.infrastructure.repositories.order.base import (
    OrderRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ConfirmOrderCommand:
    order_id: UUID


class ConfirmOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        order_repository: OrderRepository,
        order_access: OrderAccess,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._order_repository = order_repository
        self._order_access = order_access
        self._transaction_manager = transaction_manager

    async def __call__(self, command: ConfirmOrderCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)

        if order is None:
            raise OrderNotFoundError(command.order_id)

        await self._order_access.ensure_can_act(
            user_id=user_id, order=order, permission=UPDATE_ORDER
        )

        if order.payment_method is PaymentMethod.ONLINE and not order.is_paid:
            raise OrderNotPaidError()

        if order.number is None:
            order.assign_number(
                await self._order_repository.next_number(
                    order.org_unit_id, order.created_at.date()
                )
            )

        order.set_status(OrderStatus.CONFIRMED)
        await self._order_repository.save(order)
        await self._transaction_manager.commit()

        logger.info("Заказ подтверждён", extra={"order_id": str(order.id)})
