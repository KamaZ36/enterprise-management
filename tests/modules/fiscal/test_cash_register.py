from datetime import UTC, datetime
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.errors import (
    AlreadyBoundError,
    BindingConflictError,
    InactiveCashRegisterError,
    InvalidBindingPeriodError,
    InvalidRegNumberError,
    NoOpenBindingError,
    RegNumberRequiredError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)

REG_NUMBER = "0000000000051264"
START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def make_register(**kwargs) -> CashRegister:
    return CashRegister.create(
        name="Касса", reg_number=RegNumber.parse(REG_NUMBER), **kwargs
    )


def test_reg_number_must_have_16_digits() -> None:
    with pytest.raises(InvalidRegNumberError):
        RegNumber.parse("123")


def test_reg_number_normalizes_spaces_and_dashes() -> None:
    reg_number = RegNumber.parse("0000 0000 0005-1264")

    assert reg_number == RegNumber.parse(REG_NUMBER)
    assert str(reg_number) == REG_NUMBER


def test_name_falls_back_to_fiscal_place() -> None:
    register = CashRegister.create(name=None, fiscal_place="Подсобка")

    assert register.name == "Подсобка"


def test_name_falls_back_to_reg_number() -> None:
    register = CashRegister.create(
        name=None, reg_number=RegNumber.parse(REG_NUMBER)
    )

    assert register.name == f"ККТ {REG_NUMBER}"


def test_name_falls_back_to_default() -> None:
    register = CashRegister.create()

    assert register.name == "Касса"


def test_binding_requires_reg_number() -> None:
    register = CashRegister.create(name="Касса")

    with pytest.raises(RegNumberRequiredError):
        register.plan_binding(org_unit_id=uuid4(), effective_from=START)


def test_first_binding_stays_open() -> None:
    register = make_register()
    shop_id = uuid4()

    plan = register.plan_binding(org_unit_id=shop_id, effective_from=START)

    assert plan.binding.org_unit_id == shop_id
    assert plan.binding.effective_to is None
    assert plan.closes is None


def test_rebinding_closes_previous_binding() -> None:
    register = make_register()
    first_shop = uuid4()
    second_shop = uuid4()

    first = register.plan_binding(org_unit_id=first_shop, effective_from=START)
    second = register.plan_binding(org_unit_id=second_shop, effective_from=LATER)

    assert second.closes is first.binding
    assert first.binding.effective_to == LATER
    assert second.binding.effective_to is None


def test_binding_same_point_twice_fails() -> None:
    register = make_register()
    shop_id = uuid4()
    register.plan_binding(org_unit_id=shop_id, effective_from=START)

    with pytest.raises(AlreadyBoundError):
        register.plan_binding(org_unit_id=shop_id, effective_from=LATER)


def test_binding_before_open_binding_fails() -> None:
    register = make_register()
    register.plan_binding(org_unit_id=uuid4(), effective_from=LATER)

    with pytest.raises(BindingConflictError):
        register.plan_binding(org_unit_id=uuid4(), effective_from=START)


def test_binding_naive_datetime_fails() -> None:
    register = make_register()

    with pytest.raises(TimezoneRequiredError):
        register.plan_binding(
            org_unit_id=uuid4(), effective_from=datetime(2026, 1, 1)
        )


def test_inactive_register_cannot_be_bound() -> None:
    register = make_register()
    register.deactivate(START)

    with pytest.raises(InactiveCashRegisterError):
        register.plan_binding(org_unit_id=uuid4(), effective_from=START)


def test_unbind_without_open_binding_fails() -> None:
    register = make_register()

    with pytest.raises(NoOpenBindingError):
        register.plan_unbind(LATER)


def test_unbind_before_start_fails() -> None:
    register = make_register()
    register.plan_binding(org_unit_id=uuid4(), effective_from=LATER)

    with pytest.raises(InvalidBindingPeriodError):
        register.plan_unbind(START)


def test_unbind_closes_binding() -> None:
    register = make_register()
    register.plan_binding(org_unit_id=uuid4(), effective_from=START)

    binding = register.plan_unbind(LATER)

    assert binding.effective_to == LATER


def test_binding_at_returns_binding_for_date() -> None:
    register = make_register()
    first_shop = uuid4()
    second_shop = uuid4()

    first = register.plan_binding(
        org_unit_id=first_shop, effective_from=START
    ).binding
    second = register.plan_binding(
        org_unit_id=second_shop, effective_from=LATER
    ).binding

    assert (
        register.binding_at(datetime(2026, 1, 15, tzinfo=UTC)) is first
    )
    assert (
        register.binding_at(datetime(2026, 2, 15, tzinfo=UTC)) is second
    )
    assert register.binding_at(datetime(2025, 12, 31, tzinfo=UTC)) is None


def test_deactivate_closes_open_binding() -> None:
    register = make_register()
    binding = register.plan_binding(
        org_unit_id=uuid4(), effective_from=START
    ).binding

    closed = register.deactivate(LATER)

    assert closed is binding
    assert binding.effective_to == LATER
    assert register.is_active is False
    assert register.deregistered_at == LATER
