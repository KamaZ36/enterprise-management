from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.presentation.business_api import (
    StockLocation,
)
from myasnaya_derevnya.modules.fiscal.application.errors import CashRegisterNotFound
from myasnaya_derevnya.modules.fiscal.application.interactors.bind_cash_register import (
    BindCashRegisterCommand,
    BindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.cash_register import CashRegister
from myasnaya_derevnya.modules.fiscal.domain.errors import (
    BindingTargetInactiveError,
    BindingTargetNotStockLocationError,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.reg_number import (
    RegNumber,
)
from tests.modules.fiscal.fakes import (
    FakeBusinessAPI,
    FakeCashRegisterRepository,
    FakeIdentityProvider,
    FakeStaffAPI,
    FakeTransactionManager,
)

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
LATER = datetime(2026, 2, 1, 12, 0, tzinfo=UTC)


def build(
    *,
    allowed: bool = True,
    locations: dict[UUID, StockLocation] | None = None,
    register: CashRegister | None = None,
):
    cash_register = register or CashRegister.create(
        name="Касса", reg_number=RegNumber.parse("0000000000051264")
    )
    repository = FakeCashRegisterRepository([cash_register])
    transaction_manager = FakeTransactionManager()
    interactor = BindCashRegisterInteractor(
        identity_provider=FakeIdentityProvider(),
        cash_register_repository=repository,
        business_api=FakeBusinessAPI(locations=locations),
        transaction_manager=transaction_manager,
        staff_api=FakeStaffAPI(allowed=allowed),
    )

    return cash_register, repository, transaction_manager, interactor


def active_location(org_unit_id: UUID) -> StockLocation:
    return StockLocation(
        id=org_unit_id, code="SHOP-01", name="Магазин", is_active=True
    )


async def test_bind_adds_binding() -> None:
    shop_id = uuid4()
    register, repository, transaction_manager, interactor = build(
        locations={shop_id: active_location(shop_id)}
    )

    await interactor(
        BindCashRegisterCommand(
            cash_register_id=register.id,
            org_unit_id=shop_id,
            effective_from=START,
        )
    )

    assert len(repository.bindings) == 1
    assert repository.bindings[0].org_unit_id == shop_id
    assert repository.bindings[0].effective_to is None
    assert transaction_manager.commits == 1


async def test_rebind_closes_previous_binding() -> None:
    first_shop = uuid4()
    second_shop = uuid4()
    register, repository, _, interactor = build(
        locations={
            first_shop: active_location(first_shop),
            second_shop: active_location(second_shop),
        }
    )
    register.plan_binding(org_unit_id=first_shop, effective_from=START)

    await interactor(
        BindCashRegisterCommand(
            cash_register_id=register.id,
            org_unit_id=second_shop,
            effective_from=LATER,
        )
    )

    assert len(repository.closed) == 1
    assert repository.closed[0].effective_to == LATER
    assert repository.bindings[0].org_unit_id == second_shop


async def test_bind_requires_stock_location() -> None:
    register, _, _, interactor = build()

    with pytest.raises(BindingTargetNotStockLocationError):
        await interactor(
            BindCashRegisterCommand(
                cash_register_id=register.id,
                org_unit_id=uuid4(),
                effective_from=START,
            )
        )


async def test_bind_requires_active_location() -> None:
    shop_id = uuid4()
    location = StockLocation(
        id=shop_id, code="SHOP-01", name="Магазин", is_active=False
    )
    register, _, _, interactor = build(locations={shop_id: location})

    with pytest.raises(BindingTargetInactiveError):
        await interactor(
            BindCashRegisterCommand(
                cash_register_id=register.id,
                org_unit_id=shop_id,
                effective_from=START,
            )
        )


async def test_bind_requires_permission() -> None:
    shop_id = uuid4()
    register, _, _, interactor = build(
        allowed=False, locations={shop_id: active_location(shop_id)}
    )

    with pytest.raises(ForbiddenError):
        await interactor(
            BindCashRegisterCommand(
                cash_register_id=register.id,
                org_unit_id=shop_id,
                effective_from=START,
            )
        )


async def test_bind_unknown_register_fails() -> None:
    shop_id = uuid4()
    _, _, _, interactor = build(
        locations={shop_id: active_location(shop_id)}
    )

    with pytest.raises(CashRegisterNotFound):
        await interactor(
            BindCashRegisterCommand(
                cash_register_id=uuid4(),
                org_unit_id=shop_id,
                effective_from=START,
            )
        )
