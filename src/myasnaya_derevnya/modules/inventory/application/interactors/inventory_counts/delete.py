import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
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
class DeleteInventoryCountCommand:
    inventory_count_id: UUID


class DeleteInventoryCountInteractor:
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

    async def __call__(self, command: DeleteInventoryCountCommand) -> None:
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

        await self._inventory_count_repository.delete(inventory_count.id)
        await self._transaction_manager.commit()

        logger.info(
            "Черновик инвентаризации удалён",
            extra={"inventory_count_id": str(inventory_count.id)},
        )
