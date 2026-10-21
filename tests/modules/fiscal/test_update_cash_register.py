from datetime import UTC, datetime
from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.fiscal.application.interactors.update_cash_register import (
    UpdateCashRegisterCommand,
    UpdateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from tests.modules.fiscal.fakes import (
    FakeCashRegisterRepository,
    FakeIdentityProvider,
    FakeStaffAPI,
    FakeTransactionManager,
)

REG_NUMBER = "0000000000051264"
START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def build(register: CashRegister, *, allowed: bool = True):
    repository = FakeCashRegisterRepository([register])
    transaction_manager = FakeTransactionManager()
    interactor = UpdateCashRegisterInteractor(
        identity_provider=FakeIdentityProvider(),
        cash_register_repository=repository,
        transaction_manager=transaction_manager,
        staff_api=FakeStaffAPI(allowed=allowed),
    )

    return repository, transaction_manager, interactor


async def test_update_changes_name() -> None:
    register = CashRegister.create(name="Старая", reg_number=RegNumber.parse(REG_NUMBER))
    repository, transaction_manager, interactor = build(register)

    await interactor(
        UpdateCashRegisterCommand(
            cash_register_id=register.id,
            provided=frozenset({"name"}),
            name="Новая",
        )
    )

    assert register.name == "Новая"
    assert repository.saved == [register]
    assert transaction_manager.commits == 1


async def test_update_reg_number_normalizes_value() -> None:
    register = CashRegister.create(name="Касса", reg_number=RegNumber.parse(REG_NUMBER))
    _, _, interactor = build(register)

    await interactor(
        UpdateCashRegisterCommand(
            cash_register_id=register.id,
            provided=frozenset({"reg_number"}),
            reg_number="0000 0000 0005-1264",
        )
    )

    assert str(register.reg_number) == REG_NUMBER


async def test_deactivation_closes_open_binding() -> None:
    register = CashRegister.create(name="Касса", reg_number=RegNumber.parse(REG_NUMBER))
    register.plan_binding(org_unit_id=uuid4(), effective_from=START)
    repository, _, interactor = build(register)

    await interactor(
        UpdateCashRegisterCommand(
            cash_register_id=register.id,
            provided=frozenset({"is_active"}),
            is_active=False,
        )
    )

    assert register.is_active is False
    assert len(repository.closed) == 1
    assert repository.closed[0].effective_to is not None


async def test_update_requires_permission() -> None:
    register = CashRegister.create(name="Касса", reg_number=RegNumber.parse(REG_NUMBER))
    _, _, interactor = build(register, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(
            UpdateCashRegisterCommand(
                cash_register_id=register.id,
                provided=frozenset({"name"}),
                name="Новая",
            )
        )
