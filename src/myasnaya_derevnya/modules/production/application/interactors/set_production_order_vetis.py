import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import (
    TransactionManager,
)
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    ProductionLocationNotFoundError,
    ProductionOrderNotFoundError,
)
from myasnaya_derevnya.modules.production.domain.permissions import MANAGE_ORDERS
from myasnaya_derevnya.modules.production.domain.value_objects.vetis_status import (
    VetisStatus,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProductionOutputVetisCommand:
    line_id: UUID
    production_vsd_number: str | None = None
    production_vsd_guid: UUID | None = None
    batch_id: str | None = None


@dataclass(frozen=True, slots=True)
class SetProductionOrderVetisCommand:
    order_id: UUID
    status: VetisStatus
    operation_id: str | None = None
    no_vsd_reason: str | None = None
    outputs: tuple[ProductionOutputVetisCommand, ...] = ()


class SetProductionOrderVetisInteractor:
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

    async def __call__(self, command: SetProductionOrderVetisCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        order = await self._order_repository.get_by_id(command.order_id)
        if order is None:
            raise ProductionOrderNotFoundError(command.order_id)

        location = await self._inventory_api.get_location(order.org_unit_id)
        if location is None:
            raise ProductionLocationNotFoundError(order.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=MANAGE_ORDERS,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        order.set_vetis(
            status=command.status,
            operation_id=command.operation_id,
            no_vsd_reason=command.no_vsd_reason,
            entered_by=user_id,
        )

        for output in command.outputs:
            order.set_output_vetis(
                line_id=output.line_id,
                production_vsd_number=output.production_vsd_number,
                production_vsd_guid=output.production_vsd_guid,
                batch_id=output.batch_id,
            )

            line = next(
                (item for item in order.lines if item.id == output.line_id),
                None,
            )
            if line is None or line.lot_id is None:
                continue

            if not any(
                value is not None
                for value in (
                    output.production_vsd_number,
                    output.production_vsd_guid,
                    output.batch_id,
                )
            ):
                continue

            await self._inventory_api.set_lot_vetis(
                lot_id=line.lot_id,
                vsd_number=output.production_vsd_number,
                vsd_guid=output.production_vsd_guid,
                batch_id=output.batch_id,
                entered_by=user_id,
            )

        await self._order_repository.save(order)
        await self._transaction_manager.commit()

        logger.info(
            "Реквизиты ВетИСа производственного задания сохранены",
            extra={"production_order_id": str(order.id)},
        )
