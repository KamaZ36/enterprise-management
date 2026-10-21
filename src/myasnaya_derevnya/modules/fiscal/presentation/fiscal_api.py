from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.fiscal.domain.errors import InvalidRegNumberError
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)


@dataclass(frozen=True, slots=True)
class CashRegisterInfo:
    id: UUID
    reg_number: str
    name: str


class FiscalAPI:
    """Фасад для будущего разбора чеков ОФД."""

    def __init__(self, cash_register_repository: CashRegisterRepository) -> None:
        self._cash_register_repository = cash_register_repository

    async def cash_register_by_reg_number(
        self, reg_number: str
    ) -> CashRegisterInfo | None:
        normalized = self._normalize(reg_number)
        if normalized is None:
            return None

        cash_register = await self._cash_register_repository.get_by_reg_number(
            normalized.value
        )
        if cash_register is None or cash_register.reg_number is None:
            return None

        return CashRegisterInfo(
            id=cash_register.id,
            reg_number=cash_register.reg_number.value,
            name=cash_register.name,
        )

    async def cash_register_location_at(
        self, reg_number: str, at: datetime
    ) -> UUID | None:
        normalized = self._normalize(reg_number)
        if normalized is None:
            return None

        cash_register = await self._cash_register_repository.get_by_reg_number(
            normalized.value
        )
        if cash_register is None:
            return None

        binding = cash_register.binding_at(at)
        if binding is None:
            return None

        return binding.org_unit_id

    @staticmethod
    def _normalize(reg_number: str) -> RegNumber | None:
        try:
            return RegNumber.parse(reg_number)
        except InvalidRegNumberError:
            return None
