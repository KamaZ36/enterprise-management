from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.domain.errors import OrderNotFoundError
from myasnaya_derevnya.modules.sales.domain.permissions import UPDATE_ORDER
from myasnaya_derevnya.modules.sales.domain.value_objects.order_status import (
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)


@dataclass(frozen=True, slots=True)
class MarkOrderReadyCommand:
    order_id: UUID


class MarkOrderReadyInteractor:
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

    async def __call__(self, command: MarkOrderReadyCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)
        if order is None:
            raise OrderNotFoundError(command.order_id)

        await self._order_access.ensure_is_staff(
            user_id=user_id, order=order, permission=UPDATE_ORDER
        )

        order.set_status(OrderStatus.READY)
        await self._order_repository.save(order)
        await self._transaction_manager.commit()
