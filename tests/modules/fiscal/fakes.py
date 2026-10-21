from uuid import UUID, uuid4

from myasnaya_derevnya.modules.business.presentation.business_api import (
    StockLocation,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register_binding import (
    CashRegisterBinding,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID | None = None) -> None:
        self.user_id = user_id or uuid4()

    async def get_current_user_id(self) -> UUID:
        return self.user_id

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(
        self,
        *,
        allowed: bool = True,
        scope: AccessScope | None = None,
    ) -> None:
        self.allowed = allowed
        self.scope = scope if scope is not None else AccessScope.company_wide()

    async def can(
        self, user_id: UUID, permission: object, org_unit_id: UUID | None
    ) -> bool:
        return self.allowed

    async def can_anywhere(self, *, user_id: UUID, permission: object) -> bool:
        return self.allowed

    async def scope_for(self, *, user_id: UUID, permission: object) -> AccessScope:
        return self.scope


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        return None


class FakeBusinessAPI:
    def __init__(
        self,
        *,
        locations: dict[UUID, StockLocation] | None = None,
        titles: dict[UUID, str] | None = None,
    ) -> None:
        self.locations = locations or {}
        self.titles = titles or {}

    async def stock_location(self, org_unit_id: UUID) -> StockLocation | None:
        return self.locations.get(org_unit_id)

    async def stock_locations(self) -> list[StockLocation]:
        return list(self.locations.values())

    async def org_unit_titles(self, org_unit_ids) -> dict[UUID, str]:
        return {
            org_unit_id: self.titles[org_unit_id]
            for org_unit_id in org_unit_ids
            if org_unit_id in self.titles
        }


class FakeCashRegisterRepository:
    def __init__(self, registers: list[CashRegister] | None = None) -> None:
        self.registers = {register.id: register for register in registers or []}
        self.added: list[CashRegister] = []
        self.saved: list[CashRegister] = []
        self.bindings: list[CashRegisterBinding] = []
        self.closed: list[CashRegisterBinding] = []

    async def add(self, cash_register: CashRegister) -> None:
        self.registers[cash_register.id] = cash_register
        self.added.append(cash_register)

    async def save(self, cash_register: CashRegister) -> None:
        self.saved.append(cash_register)

    async def get_by_id(self, cash_register_id: UUID) -> CashRegister | None:
        return self.registers.get(cash_register_id)

    async def get_by_reg_number(self, reg_number: str) -> CashRegister | None:
        for register in self.registers.values():
            if (
                register.reg_number is not None
                and register.reg_number.value == reg_number
            ):
                return register

        return None

    async def add_binding(self, binding: CashRegisterBinding) -> None:
        self.bindings.append(binding)

    async def close_binding(self, binding: CashRegisterBinding) -> None:
        self.closed.append(binding)
