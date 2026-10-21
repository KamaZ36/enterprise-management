from datetime import UTC, datetime
from uuid import uuid4

from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from myasnaya_derevnya.modules.fiscal.presentation.fiscal_api import FiscalAPI
from tests.modules.fiscal.fakes import FakeCashRegisterRepository

REG_NUMBER = "0000000000051264"
START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
JANUARY = datetime(2026, 1, 15, tzinfo=UTC)


def build(register: CashRegister | None = None) -> FiscalAPI:
    registers = [register] if register is not None else []

    return FiscalAPI(
        cash_register_repository=FakeCashRegisterRepository(registers)
    )


async def test_finds_register_by_normalized_reg_number() -> None:
    register = CashRegister.create(name="Касса", reg_number=RegNumber.parse(REG_NUMBER))
    api = build(register)

    info = await api.cash_register_by_reg_number("0000 0000 0005-1264")

    assert info is not None
    assert info.id == register.id
    assert info.reg_number == REG_NUMBER


async def test_returns_none_for_unknown_or_invalid_reg_number() -> None:
    api = build()

    assert await api.cash_register_by_reg_number(REG_NUMBER) is None
    assert await api.cash_register_by_reg_number("123") is None


async def test_resolves_location_at_receipt_time() -> None:
    shop_id = uuid4()
    register = CashRegister.create(name="Касса", reg_number=RegNumber.parse(REG_NUMBER))
    register.plan_binding(org_unit_id=shop_id, effective_from=START)
    api = build(register)

    assert (
        await api.cash_register_location_at(REG_NUMBER, JANUARY) == shop_id
    )
    assert (
        await api.cash_register_location_at(
            REG_NUMBER, datetime(2025, 1, 1, tzinfo=UTC)
        )
        is None
    )
