from dataclasses import replace
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem
from myasnaya_derevnya.modules.inventory.application.interactors.balances.read import (
    GetBalanceInteractor,
    GetBalanceQuery,
    ListBalancesInteractor,
    ListBalancesQuery,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import WarehouseNotFoundError
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


class FakeWarehouseRepository:
    def __init__(self, warehouse: Warehouse | None) -> None:
        self._warehouse = warehouse

    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        if self._warehouse is None:
            return None

        return self._warehouse if self._warehouse.id == warehouse_id else None


class FakeBalanceReader:
    def __init__(self, items: list[BalanceListItem]) -> None:
        self._items = items
        self.with_cost_calls: list[bool] = []

    async def list_by_warehouse(
        self, warehouse_id: UUID, *, with_cost: bool
    ) -> list[BalanceListItem]:
        self.with_cost_calls.append(with_cost)

        return [
            self._mask(item, with_cost)
            for item in self._items
            if item.warehouse_id == warehouse_id
        ]

    async def get(
        self, warehouse_id: UUID, nomenclature_id: UUID, *, with_cost: bool
    ) -> BalanceListItem | None:
        self.with_cost_calls.append(with_cost)

        found = next(
            (
                item
                for item in self._items
                if item.warehouse_id == warehouse_id
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


def make_warehouse() -> Warehouse:
    return Warehouse.create(
        org_unit_id=uuid4(), code="RAW-01", name="Склад сырья", type=WarehouseType.RAW
    )


def make_balance(
    warehouse_id: UUID, nomenclature_id: UUID, *, quantity: str = "10"
) -> BalanceListItem:
    return BalanceListItem(
        warehouse_id=warehouse_id,
        nomenclature_id=nomenclature_id,
        quantity=Decimal(quantity),
        average_unit_cost=Decimal(450),
        total_value_kopecks=450000,
    )


def build_get(
    warehouse: Warehouse | None,
    items: list[BalanceListItem],
    *,
    denied: set[str] | None = None,
    names: dict[UUID, str] | None = None,
):
    reader = FakeBalanceReader(items)
    staff_api = FakeStaffAPI(denied)
    interactor = GetBalanceInteractor(
        identity_provider=FakeIdentityProvider(),
        warehouse_repository=FakeWarehouseRepository(warehouse),
        balance_reader=reader,
        catalog_api=FakeCatalogAPI(names),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


def build_list(
    warehouse: Warehouse | None,
    items: list[BalanceListItem],
    *,
    denied: set[str] | None = None,
    names: dict[UUID, str] | None = None,
):
    reader = FakeBalanceReader(items)
    staff_api = FakeStaffAPI(denied)
    interactor = ListBalancesInteractor(
        identity_provider=FakeIdentityProvider(),
        warehouse_repository=FakeWarehouseRepository(warehouse),
        balance_reader=reader,
        catalog_api=FakeCatalogAPI(names),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_get_balance_requires_read_permission() -> None:
    warehouse = make_warehouse()
    interactor, _, _ = build_get(warehouse, [], denied={READ_BALANCES.code})

    with pytest.raises(ForbiddenError):
        await interactor(GetBalanceQuery(warehouse.id, uuid4()))


async def test_get_balance_raises_when_warehouse_is_unknown() -> None:
    interactor, _, _ = build_get(None, [])

    with pytest.raises(WarehouseNotFoundError):
        await interactor(GetBalanceQuery(uuid4(), uuid4()))


async def test_get_balance_hides_cost_without_cost_permission() -> None:
    warehouse = make_warehouse()
    nomenclature_id = uuid4()
    item = make_balance(warehouse.id, nomenclature_id)
    interactor, reader, staff_api = build_get(
        warehouse, [item], denied={READ_COSTS.code}
    )

    result = await interactor(GetBalanceQuery(warehouse.id, nomenclature_id))
    schema = BalanceSchema.from_dto(result)

    assert reader.with_cost_calls == [False]
    assert result.quantity == Decimal(10)
    assert schema.average_unit_cost is None
    assert schema.total_value_kopecks is None
    assert staff_api.checked == [READ_BALANCES.code, READ_COSTS.code]


async def test_get_balance_shows_cost_with_cost_permission() -> None:
    warehouse = make_warehouse()
    nomenclature_id = uuid4()
    item = make_balance(warehouse.id, nomenclature_id)
    interactor, reader, _ = build_get(
        warehouse, [item], names={nomenclature_id: "Говядина лопатка"}
    )

    result = await interactor(GetBalanceQuery(warehouse.id, nomenclature_id))
    schema = BalanceSchema.from_dto(result)

    assert reader.with_cost_calls == [True]
    assert schema.average_unit_cost == Decimal(450)
    assert schema.total_value_kopecks == 450000
    assert schema.nomenclature_name == "Говядина лопатка"


async def test_get_balance_returns_empty_balance_when_row_is_missing() -> None:
    warehouse = make_warehouse()
    interactor, _, _ = build_get(warehouse, [])

    result = await interactor(GetBalanceQuery(warehouse.id, uuid4()))

    assert result.quantity == Decimal(0)
    assert result.total_value_kopecks == 0


async def test_list_balances_returns_items_with_names() -> None:
    warehouse = make_warehouse()
    nomenclature_id = uuid4()
    item = make_balance(warehouse.id, nomenclature_id)
    interactor, reader, _ = build_list(
        warehouse, [item], names={nomenclature_id: "Говядина лопатка"}
    )

    items = await interactor(ListBalancesQuery(warehouse.id))

    assert len(items) == 1
    assert isinstance(items[0], BalanceListItem)
    assert items[0].nomenclature_name == "Говядина лопатка"
    assert reader.with_cost_calls == [True]


async def test_list_balances_filters_by_name() -> None:
    warehouse = make_warehouse()
    first = make_balance(warehouse.id, uuid4())
    second = make_balance(warehouse.id, uuid4())
    names = {
        first.nomenclature_id: "Говядина лопатка",
        second.nomenclature_id: "Свинина шея",
    }
    interactor, _, _ = build_list(warehouse, [first, second], names=names)

    items = await interactor(ListBalancesQuery(warehouse.id, search="свинина"))

    assert [item.nomenclature_name for item in items] == ["Свинина шея"]


async def test_list_balances_without_search_returns_everything() -> None:
    warehouse = make_warehouse()
    first = make_balance(warehouse.id, uuid4())
    second = make_balance(warehouse.id, uuid4())
    interactor, _, _ = build_list(warehouse, [first, second])

    items = await interactor(ListBalancesQuery(warehouse.id))

    assert len(items) == 2
