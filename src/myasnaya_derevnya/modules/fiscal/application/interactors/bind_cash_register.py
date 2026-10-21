import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.fiscal.application.errors import CashRegisterNotFound
from myasnaya_derevnya.modules.fiscal.domain.errors import (
    BindingTargetInactiveError,
    BindingTargetNotStockLocationError,
)
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_MANAGE
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BindCashRegisterCommand:
    cash_register_id: UUID
    org_unit_id: UUID
    effective_from: datetime | None = None


class BindCashRegisterInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        cash_register_repository: CashRegisterRepository,
        business_api: BusinessAPI,
        transaction_manager: TransactionManager,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._cash_register_repository = cash_register_repository
        self._business_api = business_api
        self._transaction_manager = transaction_manager
        self._staff_api = staff_api

    async def __call__(self, command: BindCashRegisterCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=CASH_REGISTER_MANAGE
        ):
            raise ForbiddenError()

        location = await self._business_api.stock_location(command.org_unit_id)
        if location is None:
            raise BindingTargetNotStockLocationError(command.org_unit_id)

        if not location.is_active:
            raise BindingTargetInactiveError(command.org_unit_id)

        cash_register = await self._cash_register_repository.get_by_id(
            command.cash_register_id
        )
        if cash_register is None:
            raise CashRegisterNotFound(command.cash_register_id)

        plan = cash_register.plan_binding(
            org_unit_id=command.org_unit_id,
            effective_from=command.effective_from or get_datetime_utc(),
        )

        if plan.closes is not None:
            await self._cash_register_repository.close_binding(plan.closes)

        await self._cash_register_repository.add_binding(plan.binding)
        await self._transaction_manager.commit()

        logger.info(
            "Касса привязана",
            extra={
                "cash_register_id": str(cash_register.id),
                "org_unit_id": str(command.org_unit_id),
            },
        )
