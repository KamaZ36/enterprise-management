from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.fiscal.application.dto import CashRegisterListItem
from myasnaya_derevnya.modules.fiscal.application.interactors.list_cash_registers import (
    ListCashRegistersInteractor,
    ListCashRegistersQuery,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)
from tests.modules.fiscal.fakes import (
    FakeBusinessAPI,
    FakeIdentityProvider,
    FakeStaffAPI,
)

AT = datetime(2026, 1, 15, tzinfo=UTC)


class FakeCashRegisterReader:
    def __init__(self, items: list[CashRegisterListItem]) -> None:
        self.items = items

    async def list(
        self, *, org_unit_id: UUID | None, at: datetime
    ) -> list[CashRegisterListItem]:
        return self.items

    async def get(self, cash_register_id: UUID):
        return None


def make_item(
    *,
    org_unit_id: UUID | None = None,
    name: str = "Касса",
) -> CashRegisterListItem:
    return CashRegisterListItem(
        id=uuid4(),
        reg_number="0000000000051264",
        serial_number=None,
        name=name,
        fiscal_place=None,
        model=None,
        fn_number=None,
        ffd_version=None,
        company_id=None,
        registered_at=None,
        deregistered_at=None,
        is_active=True,
        org_unit_id=org_unit_id,
    )


def build_list_interactor(items, *, scope: AccessScope):
    return ListCashRegistersInteractor(
        identity_provider=FakeIdentityProvider(),
        cash_register_reader=FakeCashRegisterReader(items),
        business_api=FakeBusinessAPI(
            titles={
                item.org_unit_id: f"Точка {index}"
                for index, item in enumerate(items)
                if item.org_unit_id is not None
            }
        ),
        staff_api=FakeStaffAPI(scope=scope),
    )


async def test_list_returns_all_registers_for_company_wide_scope() -> None:
    bound = make_item(org_unit_id=uuid4(), name="Привязанная")
    unbound = make_item(name="Свободная")
    interactor = build_list_interactor(
        [bound, unbound], scope=AccessScope.company_wide()
    )

    items = await interactor(ListCashRegistersQuery(at=AT))

    assert len(items) == 2
    assert items[0].org_unit_name == "Точка 0"
    assert items[1].org_unit_name is None


async def test_list_filters_by_scope() -> None:
    allowed_shop = uuid4()
    other_shop = uuid4()
    allowed = make_item(org_unit_id=allowed_shop)
    other = make_item(org_unit_id=other_shop)
    interactor = build_list_interactor(
        [allowed, other], scope=AccessScope.of([allowed_shop])
    )

    items = await interactor(ListCashRegistersQuery(at=AT))

    assert [item.id for item in items] == [allowed.id]


async def test_scoped_list_hides_unbound_registers() -> None:
    shop_id = uuid4()
    bound = make_item(org_unit_id=shop_id)
    unbound = make_item()
    interactor = build_list_interactor(
        [bound, unbound], scope=AccessScope.of([shop_id])
    )

    items = await interactor(ListCashRegistersQuery(at=AT))

    assert [item.id for item in items] == [bound.id]


async def test_empty_scope_is_forbidden() -> None:
    interactor = build_list_interactor([], scope=AccessScope.of([]))

    with pytest.raises(ForbiddenError):
        await interactor(ListCashRegistersQuery(at=AT))
