from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionWarehouseNotFoundError,
    TechCardNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import MANAGE_ORDERS
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.base import (
    TechCardRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class CreateProductionOrderCommand:
    warehouse_id: UUID
    tech_card_id: UUID
    batch_count: Decimal
    occurred_at: datetime
    comment: str | None = None


class CreateProductionOrderInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        inventory_api: InventoryAPI,
        tech_card_repository: TechCardRepository,
        order_repository: ProductionOrderRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._inventory_api = inventory_api
        self._tech_card_repository = tech_card_repository
        self._order_repository = order_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateProductionOrderCommand) -> UUID:
        user_id = await self._identity_provider.get_current_user_id()

        tech_card = await self._tech_card_repository.get_by_id(command.tech_card_id)
        if tech_card is None:
            raise TechCardNotFoundError(command.tech_card_id)

        warehouse = await self._inventory_api.get_warehouse(command.warehouse_id)
        if warehouse is None:
            raise ProductionWarehouseNotFoundError(command.warehouse_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=MANAGE_ORDERS,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        order = ProductionOrder.create(
            warehouse_id=command.warehouse_id,
            tech_card=tech_card,
            batch_count=command.batch_count,
            occurred_at=command.occurred_at,
            created_by=user_id,
            comment=command.comment,
        )

        await self._order_repository.add(order)
        await self._transaction_manager.commit()

        return order.id
