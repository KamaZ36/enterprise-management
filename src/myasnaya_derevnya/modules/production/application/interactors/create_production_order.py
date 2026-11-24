import logging
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
    ManualProductionLine,
    ProductionOrder,
)
from myasnaya_derevnya.modules.production.domain.errors import (
    EmptyBatchError,
    ProductionLocationNotFoundError,
    ProductionLocationTypeError,
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ManualProductionLineCommand:
    nomenclature_id: UUID
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class CreateProductionOrderCommand:
    org_unit_id: UUID
    occurred_at: datetime
    tech_card_id: UUID | None = None
    batch_count: Decimal | None = None
    components: tuple[ManualProductionLineCommand, ...] = ()
    outputs: tuple[ManualProductionLineCommand, ...] = ()
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

        tech_card = None
        batch_count = None

        if command.tech_card_id is not None:
            tech_card = await self._tech_card_repository.get_by_id(
                command.tech_card_id
            )
            if tech_card is None:
                raise TechCardNotFoundError(command.tech_card_id)
            if command.batch_count is None or command.batch_count <= 0:
                raise EmptyBatchError()
            batch_count = command.batch_count

        location = await self._inventory_api.get_location(command.org_unit_id)
        if location is None:
            raise ProductionLocationNotFoundError(command.org_unit_id)
        if location.type != "production":
            raise ProductionLocationTypeError()

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=MANAGE_ORDERS,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        if tech_card is None:
            order = ProductionOrder.create_manual(
                org_unit_id=command.org_unit_id,
                components=[
                    ManualProductionLine(
                        nomenclature_id=line.nomenclature_id,
                        quantity=line.quantity,
                    )
                    for line in command.components
                ],
                outputs=[
                    ManualProductionLine(
                        nomenclature_id=line.nomenclature_id,
                        quantity=line.quantity,
                    )
                    for line in command.outputs
                ],
                occurred_at=command.occurred_at,
                created_by=user_id,
                comment=command.comment,
            )
        else:
            order = ProductionOrder.create(
                org_unit_id=command.org_unit_id,
                tech_card=tech_card,
                batch_count=batch_count,
                occurred_at=command.occurred_at,
                created_by=user_id,
                comment=command.comment,
            )

        await self._order_repository.add(order)
        await self._transaction_manager.commit()

        logger.info(
            "Создан производственный заказ",
            extra={
                "production_order_id": str(order.id),
                "org_unit_id": str(order.org_unit_id),
                "tech_card_id": str(order.tech_card_id),
            },
        )

        return order.id
