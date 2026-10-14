from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionOrderNotFoundError,
    ProductionWarehouseNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import MANAGE_ORDERS
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class ProductionOrderActualCommand:
    line_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class UpdateProductionOrderCommand:
    order_id: UUID
    actuals: tuple[ProductionOrderActualCommand, ...]


class UpdateProductionOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        inventory_api: InventoryAPI,
        order_repository: ProductionOrderRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._inventory_api = inventory_api
        self._order_repository = order_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateProductionOrderCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)
        if order is None:
            raise ProductionOrderNotFoundError(command.order_id)

        warehouse = await self._inventory_api.get_warehouse(order.warehouse_id)
        if warehouse is None:
            raise ProductionWarehouseNotFoundError(order.warehouse_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=MANAGE_ORDERS,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        for actual in command.actuals:
            order.set_actual(actual.line_id, actual.quantity)

        await self._order_repository.save(order)
        await self._transaction_manager.commit()
