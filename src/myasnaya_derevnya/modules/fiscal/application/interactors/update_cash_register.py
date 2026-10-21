import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.fiscal.application.errors import CashRegisterNotFound
from myasnaya_derevnya.modules.fiscal.domain.permissions import CASH_REGISTER_MANAGE
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateCashRegisterCommand:
    cash_register_id: UUID
    provided: frozenset[str]
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
    is_active: bool | None = None


class UpdateCashRegisterInteractor:
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

    async def __call__(self, command: UpdateCashRegisterCommand) -> None:
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

        name = command.name if "name" in command.provided else cash_register.name
        if "reg_number" in command.provided:
            reg_number = (
                RegNumber.parse(command.reg_number)
                if command.reg_number
                else None
            )
        else:
            reg_number = cash_register.reg_number
        serial_number = (
            command.serial_number
            if "serial_number" in command.provided
            else cash_register.serial_number
        )
        fiscal_place = (
            command.fiscal_place
            if "fiscal_place" in command.provided
            else cash_register.fiscal_place
        )
        model = command.model if "model" in command.provided else cash_register.model
        fn_number = (
            command.fn_number
            if "fn_number" in command.provided
            else cash_register.fn_number
        )
        ffd_version = (
            command.ffd_version
            if "ffd_version" in command.provided
            else cash_register.ffd_version
        )
        company_id = (
            command.company_id
            if "company_id" in command.provided
            else cash_register.company_id
        )
        registered_at = (
            command.registered_at
            if "registered_at" in command.provided
            else cash_register.registered_at
        )
        attributes = (
            command.attributes
            if "attributes" in command.provided
            else cash_register.attributes
        )

        cash_register.change_details(
            name=name,
            reg_number=reg_number,
            serial_number=serial_number,
            fiscal_place=fiscal_place,
            model=model,
            fn_number=fn_number,
            ffd_version=ffd_version,
            company_id=company_id,
            registered_at=registered_at,
            attributes=attributes,
        )

        closed_binding = None
        if command.is_active is not None:
            if command.is_active:
                cash_register.activate()
            else:
                closed_binding = cash_register.deactivate(get_datetime_utc())

        await self._cash_register_repository.save(cash_register)

        if closed_binding is not None:
            await self._cash_register_repository.close_binding(closed_binding)

        await self._transaction_manager.commit()

        logger.info(
            "Касса изменена",
            extra={
                "cash_register_id": str(cash_register.id),
                "changed_fields": sorted(command.provided),
            },
        )
