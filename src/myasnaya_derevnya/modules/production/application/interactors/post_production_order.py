from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
    ProductionIssue,
    ProductionReceipt,
)
from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionOrderNotFoundError,
    ProductionWarehouseNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import POST_ORDER
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


class PostProductionOrderInteractor:
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

    async def __call__(self, order_id: UUID) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(order_id)
        if order is None:
            raise ProductionOrderNotFoundError(order_id)

        warehouse = await self._inventory_api.get_warehouse(order.warehouse_id)
        if warehouse is None:
            raise ProductionWarehouseNotFoundError(order.warehouse_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POST_ORDER,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()


        order.post()

        issues = [line for line in order.components if line.actual_quantity > 0]
        outputs = [line for line in order.outputs if line.actual_quantity > 0]
        lot_code = self._lot_code(order)

        posted = await self._inventory_api.post_production(
            document_id=order.id,
            warehouse_id=order.warehouse_id,
            occurred_at=order.occurred_at,
            issues=[
                ProductionIssue(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.actual_quantity,
                )
                for line in issues
            ],
            receipts=[
                ProductionReceipt(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.actual_quantity,
                    share=line.cost_weight,
                    lot_code=lot_code,
                )
                for line in outputs
            ],
            posted_by=user_id,
        )

        order.apply_costs(
            {
                line.id: posted.receipts[index].cost_kopecks
                for index, line in enumerate(outputs)
            }
        )

        await self._order_repository.save(order)
        await self._transaction_manager.commit()

    def _lot_code(self, order: ProductionOrder) -> str:
        day = order.occurred_at.strftime("%Y%m%d")

        return f"{order.tech_card_code}-{day}-{str(order.id)[:8]}"
