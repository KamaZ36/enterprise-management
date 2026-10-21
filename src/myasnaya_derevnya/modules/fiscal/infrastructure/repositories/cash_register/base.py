from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register_binding import (
    CashRegisterBinding,
)


class CashRegisterRepository(ABC):
    @abstractmethod
    async def add(self, cash_register: CashRegister) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, cash_register: CashRegister) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, cash_register_id: UUID) -> CashRegister | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_reg_number(self, reg_number: str) -> CashRegister | None:
        raise NotImplementedError

    @abstractmethod
    async def add_binding(self, binding: CashRegisterBinding) -> None:
        raise NotImplementedError

    @abstractmethod
    async def close_binding(self, binding: CashRegisterBinding) -> None:
        raise NotImplementedError
