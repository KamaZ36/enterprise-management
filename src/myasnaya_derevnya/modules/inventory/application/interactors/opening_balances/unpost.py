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
    LocationNotFoundError,
    OpeningBalanceNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    MANAGE_OPENING_BALANCE,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.opening_balance.base import (
    OpeningBalanceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostOpeningBalanceCommand:
    opening_balance_id: UUID


class UnpostOpeningBalanceInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        opening_balance_repository: OpeningBalanceRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._opening_balance_repository = opening_balance_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UnpostOpeningBalanceCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        opening_balance = await self._opening_balance_repository.get_by_id(command.opening_balance_id)
        if opening_balance is None:
            raise OpeningBalanceNotFoundError(command.opening_balance_id)
        if opening_balance.status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(opening_balance.id)

        location = await self._business_api.stock_location(opening_balance.org_unit_id)
        if location is None:
            raise LocationNotFoundError(opening_balance.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=MANAGE_OPENING_BALANCE,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._ledger.unpost(
            document_type=DocumentType.OPENING_BALANCE,
            document_id=opening_balance.id,
        )

        opening_balance.unpost()
        await self._opening_balance_repository.save(opening_balance)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение ввода начальных остатков отменено",
            extra={
                "opening_balance_id": str(opening_balance.id),
                "org_unit_id": str(opening_balance.org_unit_id),
            },
        )
