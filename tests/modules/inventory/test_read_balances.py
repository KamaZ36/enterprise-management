from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.presentation.business_api import (
    StockLocation,
)
from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem
from myasnaya_derevnya.modules.inventory.application.interactors.balances.get import (
    GetBalanceInteractor,
    GetBalanceQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.balances.list import (
    ListBalancesInteractor,
    ListBalancesQuery,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.presentation.api.v1.schemas import (
    BalanceSchema,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    def __init__(self, location: StockLocation | None) -> None:
        self._location = location

    async def stock_location(self, org_unit_id: UUID) -> StockLocation | None:
        if self._location is None:
            return None

        return self._location if self._location.id == org_unit_id else None


class FakeBalanceReader:
    def __init__(self, items: list[BalanceListItem]) -> None:
        self._items = items
        self.with_cost_calls: list[bool] = []

    async def list_by_org_unit(
        self, org_unit_id: UUID, *, with_cost: bool
    ) -> list[BalanceListItem]:
        self.with_cost_calls.append(with_cost)

        return [
            self._mask(item, with_cost)
            for item in self._items
            if item.org_unit_id == org_unit_id
        ]

    async def get(
        self, org_unit_id: UUID, nomenclature_id: UUID, *, with_cost: bool
    ) -> BalanceListItem | None:
        self.with_cost_calls.append(with_cost)

        found = next(
            (
                item
                for item in self._items
                if item.org_unit_id == org_unit_id
                and item.nomenclature_id == nomenclature_id
            ),
            None,
        )

        return self._mask(found, with_cost) if found is not None else None

    @staticmethod
    def _mask(item: BalanceListItem, with_cost: bool) -> BalanceListItem:
        if with_cost:
            return item

        return replace(item, average_unit_cost=None, total_value_kopecks=None)


class FakeCatalogAPI:
    def __init__(self, names: dict[UUID, str] | None = None) -> None:
        self.names = names or {}

    async def nomenclature_names(self, nomenclature_ids) -> dict[UUID, str]:
        return {key: self.names[key] for key in nomenclature_ids if key in self.names}


class FakeStaffAPI:
    def __init__(self, denied: set[str] | None = None) -> None:
        self._denied = denied or set()
        self.checked: list[str] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append(permission.code)

        return permission.code not in self._denied


def make_location() -> StockLocation:
    return StockLocation(
        id=uuid4(), code="RAW-01", name="Склад сырья", is_active=True
    )


def make_balance(
    org_unit_id: UUID, nomenclature_id: UUID, *, quantity: str = "10"
) -> BalanceListItem:
    return BalanceListItem(
        org_unit_id=org_unit_id,
        nomenclature_id=nomenclature_id,
        quantity=Decimal(quantity),
        average_unit_cost=Decimal(450),
        total_value_kopecks=450000,
    )


def build_get(
    location: StockLocation | None,
    items: list[BalanceListItem],
    *,
    denied: set[str] | None = None,
    names: dict[UUID, str] | None = None,
):
    reader = FakeBalanceReader(items)
    staff_api = FakeStaffAPI(denied)
    interactor = GetBalanceInteractor(
        identity_provider=FakeIdentityProvider(),
        business_api=FakeBusinessAPI(location),
        balance_reader=reader,
        catalog_api=FakeCatalogAPI(names),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


def build_list(
    location: StockLocation | None,
    items: list[BalanceListItem],
    *,
    denied: set[str] | None = None,
    names: dict[UUID, str] | None = None,
):
    reader = FakeBalanceReader(items)
    staff_api = FakeStaffAPI(denied)
    interactor = ListBalancesInteractor(
        identity_provider=FakeIdentityProvider(),
        business_api=FakeBusinessAPI(location),
        balance_reader=reader,
        catalog_api=FakeCatalogAPI(names),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_get_balance_requires_read_permission() -> None:
    location = make_location()
    interactor, _, _ = build_get(location, [], denied={READ_BALANCES.code})

    with pytest.raises(ForbiddenError):
        await interactor(GetBalanceQuery(location.id, uuid4()))


async def test_get_balance_raises_when_location_is_unknown() -> None:
    interactor, _, _ = build_get(None, [])

    with pytest.raises(LocationNotFoundError):
        await interactor(GetBalanceQuery(uuid4(), uuid4()))


async def test_get_balance_hides_cost_without_cost_permission() -> None:
    location = make_location()
    nomenclature_id = uuid4()
    item = make_balance(location.id, nomenclature_id)
    interactor, reader, staff_api = build_get(
        location, [item], denied={READ_COSTS.code}
    )

    result = await interactor(GetBalanceQuery(location.id, nomenclature_id))
    schema = BalanceSchema.from_dto(result)

    assert reader.with_cost_calls == [False]
    assert result.quantity == Decimal(10)
    assert schema.average_unit_cost is None
    assert schema.total_value_kopecks is None
    assert staff_api.checked == [READ_BALANCES.code, READ_COSTS.code]


async def test_get_balance_shows_cost_with_cost_permission() -> None:
    location = make_location()
    nomenclature_id = uuid4()
    item = make_balance(location.id, nomenclature_id)
    interactor, reader, _ = build_get(
        location, [item], names={nomenclature_id: "Говядина лопатка"}
    )

    result = await interactor(GetBalanceQuery(location.id, nomenclature_id))
    schema = BalanceSchema.from_dto(result)

    assert reader.with_cost_calls == [True]
    assert schema.average_unit_cost == Decimal(450)
    assert schema.total_value_kopecks == 450000
    assert schema.nomenclature_name == "Говядина лопатка"


async def test_get_balance_returns_empty_balance_when_row_is_missing() -> None:
    location = make_location()
    interactor, _, _ = build_get(location, [])

    result = await interactor(GetBalanceQuery(location.id, uuid4()))

    assert result.quantity == Decimal(0)
    assert result.total_value_kopecks == 0


async def test_list_balances_returns_items_with_names() -> None:
    location = make_location()
    nomenclature_id = uuid4()
    item = make_balance(location.id, nomenclature_id)
    interactor, reader, _ = build_list(
        location, [item], names={nomenclature_id: "Говядина лопатка"}
    )

    items = await interactor(ListBalancesQuery(location.id))

    assert len(items) == 1
    assert isinstance(items[0], BalanceListItem)
    assert items[0].nomenclature_name == "Говядина лопатка"
    assert reader.with_cost_calls == [True]


async def test_list_balances_filters_by_name() -> None:
    location = make_location()
    first = make_balance(location.id, uuid4())
    second = make_balance(location.id, uuid4())
    names = {
        first.nomenclature_id: "Говядина лопатка",
        second.nomenclature_id: "Свинина шея",
    }
    interactor, _, _ = build_list(location, [first, second], names=names)

    items = await interactor(ListBalancesQuery(location.id, search="свинина"))

    assert [item.nomenclature_name for item in items] == ["Свинина шея"]


async def test_list_balances_without_search_returns_everything() -> None:
    location = make_location()
    first = make_balance(location.id, uuid4())
    second = make_balance(location.id, uuid4())
    interactor, _, _ = build_list(location, [first, second])

    items = await interactor(ListBalancesQuery(location.id))

    assert len(items) == 2
