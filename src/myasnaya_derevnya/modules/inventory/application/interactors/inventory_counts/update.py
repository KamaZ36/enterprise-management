import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.inventory_count import (
    InventoryCountLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InventoryCountNotFoundError,
    LocationNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.base import (
    InventoryCountRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateInventoryCountLineCommand:
    nomenclature_id: UUID
    counted_quantity: Decimal
    lot_code: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateInventoryCountCommand:
    inventory_count_id: UUID
    occurred_at: datetime
    lines: list[UpdateInventoryCountLineCommand]
    comment: str | None = None


class UpdateInventoryCountInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        inventory_count_repository: InventoryCountRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._inventory_count_repository = inventory_count_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateInventoryCountCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        inventory_count = await self._inventory_count_repository.get_by_id(
            command.inventory_count_id
        )
        if inventory_count is None:
            raise InventoryCountNotFoundError(command.inventory_count_id)
        if not inventory_count.is_draft:
            raise DocumentAlreadyPostedError(inventory_count.id)

        location = await self._business_api.stock_location(
            inventory_count.org_unit_id
        )
        if location is None:
            raise LocationNotFoundError(inventory_count.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        inventory_count.revise(
            occurred_at=command.occurred_at,
            comment=command.comment,
            lines=[
                InventoryCountLine.create(
                    nomenclature_id=line.nomenclature_id,
                    counted_quantity=line.counted_quantity,
                    lot_code=line.lot_code,
                )
                for line in command.lines
            ],
        )

        await self._inventory_count_repository.save(inventory_count)
        await self._transaction_manager.commit()

        logger.info(
            "Инвентаризация изменена",
            extra={"inventory_count_id": str(inventory_count.id)},
        )
