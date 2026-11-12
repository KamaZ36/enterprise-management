import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionLocationNotFoundError,
    ProductionOrderNotFoundError,
    ProductionOrderNotPostedError,
)
from myasnaya_derevnya.modules.production.domain.permissions import POST_ORDER
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostProductionOrderCommand:
    order_id: UUID


class UnpostProductionOrderInteractor:
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

    async def __call__(self, command: UnpostProductionOrderCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)
        if order is None:
            raise ProductionOrderNotFoundError(command.order_id)
        if order.status is not ProductionOrderStatus.POSTED:
            raise ProductionOrderNotPostedError()

        location = await self._inventory_api.get_location(order.org_unit_id)
        if location is None:
            raise ProductionLocationNotFoundError(order.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POST_ORDER,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._inventory_api.unpost_production(document_id=order.id)

        order.reset_posting()
        await self._order_repository.save(order)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение производственного задания отменено",
            extra={
                "production_order_id": str(order.id),
                "org_unit_id": str(order.org_unit_id),
            },
        )
