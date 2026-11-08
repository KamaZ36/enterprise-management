import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentNotPostedError,
    InventoryCountNotFoundError,
    LocationNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.base import (
    InventoryCountRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostInventoryCountCommand:
    inventory_count_id: UUID


class UnpostInventoryCountInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        inventory_count_repository: InventoryCountRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._inventory_count_repository = inventory_count_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UnpostInventoryCountCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        inventory_count = await self._inventory_count_repository.get_by_id(command.inventory_count_id)
        if inventory_count is None:
            raise InventoryCountNotFoundError(command.inventory_count_id)
        if inventory_count.status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(inventory_count.id)

        location = await self._business_api.stock_location(inventory_count.org_unit_id)
        if location is None:
            raise LocationNotFoundError(inventory_count.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._ledger.unpost(
            document_type=DocumentType.INVENTORY_COUNT,
            document_id=inventory_count.id,
        )

        inventory_count.unpost()
        await self._inventory_count_repository.save(inventory_count)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение инвентаризации отменено",
            extra={
                "inventory_count_id": str(inventory_count.id),
                "org_unit_id": str(inventory_count.org_unit_id),
            },
        )
