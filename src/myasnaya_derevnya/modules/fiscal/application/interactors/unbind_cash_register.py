import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.fiscal.application.errors import CashRegisterNotFound
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_MANAGE
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnbindCashRegisterCommand:
    cash_register_id: UUID
    effective_to: datetime | None = None


class UnbindCashRegisterInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        cash_register_repository: CashRegisterRepository,
        transaction_manager: TransactionManager,
        staff_api: StaffAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._cash_register_repository = cash_register_repository
        self._transaction_manager = transaction_manager
        self._staff_api = staff_api

    async def __call__(self, command: UnbindCashRegisterCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=CASH_REGISTER_MANAGE
        ):
            raise ForbiddenError()

        cash_register = await self._cash_register_repository.get_by_id(
            command.cash_register_id
        )
        if cash_register is None:
            raise CashRegisterNotFound(command.cash_register_id)

        binding = cash_register.plan_unbind(
            command.effective_to or get_datetime_utc()
        )

        await self._cash_register_repository.close_binding(binding)
        await self._transaction_manager.commit()

        logger.info(
            "Привязка кассы закрыта",
            extra={
                "cash_register_id": str(cash_register.id),
                "binding_id": str(binding.id),
            },
        )
