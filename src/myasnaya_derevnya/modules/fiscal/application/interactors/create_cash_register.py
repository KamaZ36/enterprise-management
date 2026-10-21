import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_MANAGE
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreateCashRegisterCommand:
    name: str | None = None
    reg_number: str | None = None
    serial_number: str | None = None
    fiscal_place: str | None = None
    model: str | None = None
    fn_number: str | None = None
    ffd_version: str | None = None
    company_id: UUID | None = None
    registered_at: datetime | None = None
    attributes: dict | None = None


class CreateCashRegisterInteractor:
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

    async def __call__(self, command: CreateCashRegisterCommand) -> UUID:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=CASH_REGISTER_MANAGE
        ):
            raise ForbiddenError()

        cash_register = CashRegister.create(
            name=command.name,
            reg_number=(
                RegNumber.parse(command.reg_number)
                if command.reg_number
                else None
            ),
            serial_number=command.serial_number,
            fiscal_place=command.fiscal_place,
            model=command.model,
            fn_number=command.fn_number,
            ffd_version=command.ffd_version,
            company_id=command.company_id,
            registered_at=command.registered_at,
            attributes=command.attributes,
        )

        await self._cash_register_repository.add(cash_register)
        await self._transaction_manager.commit()

        logger.info(
            "Касса добавлена",
            extra={"cash_register_id": str(cash_register.id)},
        )

        return cash_register.id
