"""Тесты чтения остатков: права на количество и на стоимость различаются."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.read_balances import (
    BalanceView,
    GetBalanceInteractor,
    GetBalanceQuery,
    ListBalancesInteractor,
    ListBalancesQuery,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_balance import (
    StockBalance,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    READ_BALANCES,
    READ_COSTS,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.presentation.api.v1.schemas import (
    BalanceSchema,
)
from myasnaya_derevnya.utils import get_datetime_utc


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    """Права настраиваются по коду, чтобы различать остаток и себестоимость."""

    def __init__(self, denied: set[str] | None = None) -> None:
        self._denied = denied or set()

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        return permission.code not in self._denied


class FakeWarehouseRepository:
    def __init__(self, warehouse: Warehouse) -> None:
        self._warehouse = warehouse

    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        return self._warehouse if warehouse_id == self._warehouse.id else None


class FakeStockBalanceRepository:
    def __init__(self, balance: StockBalance | None) -> None:
        self._balance = balance

    async def get(
        self, warehouse_id: UUID, nomenclature_id: UUID
    ) -> StockBalance | None:
        return self._balance

    async def list_by_warehouse(self, warehouse_id: UUID) -> list[StockBalance]:
        return [] if self._balance is None else [self._balance]


def make_warehouse() -> Warehouse:
    return Warehouse.create(
        org_unit_id=uuid4(), code="RAW-1", name="Сырьё", type=WarehouseType.RAW
    )


def make_balance(warehouse_id: UUID, nomenclature_id: UUID) -> StockBalance:
    return StockBalance(
        warehouse_id=warehouse_id,
        nomenclature_id=nomenclature_id,
        quantity=Decimal(10),
        total_value=Money(kopecks=450000),
        updated_at=get_datetime_utc(),
    )


def build_get_interactor(
    warehouse: Warehouse,
    balance: StockBalance | None,
    denied: set[str] | None = None,
) -> GetBalanceInteractor:
    return GetBalanceInteractor(
        identity_provider=FakeIdentityProvider(),
        warehouse_repository=FakeWarehouseRepository(warehouse),
        balance_repository=FakeStockBalanceRepository(balance),
        staff_api=FakeStaffAPI(denied),
    )


async def test_get_balance_requires_read_permission() -> None:
    warehouse = make_warehouse()
    interactor = build_get_interactor(warehouse, None, denied={READ_BALANCES.code})

    with pytest.raises(ForbiddenError):
        await interactor(GetBalanceQuery(warehouse.id, uuid4()))


async def test_get_balance_hides_cost_without_cost_permission() -> None:
    warehouse = make_warehouse()
    nomenclature_id = uuid4()
    balance = make_balance(warehouse.id, nomenclature_id)
    interactor = build_get_interactor(warehouse, balance, denied={READ_COSTS.code})

    view = await interactor(GetBalanceQuery(warehouse.id, nomenclature_id))

    assert view.balance.quantity == Decimal(10)
    assert view.cost_visible is False

    schema = BalanceSchema.from_view(view)
    assert schema.quantity == Decimal(10)
    assert schema.average_unit_cost is None
    assert schema.total_value_kopecks is None


async def test_get_balance_shows_cost_with_cost_permission() -> None:
    warehouse = make_warehouse()
    nomenclature_id = uuid4()
    balance = make_balance(warehouse.id, nomenclature_id)
    interactor = build_get_interactor(warehouse, balance)

    view = await interactor(GetBalanceQuery(warehouse.id, nomenclature_id))

    assert view.cost_visible is True

    schema = BalanceSchema.from_view(view)
    assert schema.average_unit_cost == Decimal(450)
    assert schema.total_value_kopecks == 450000


async def test_get_balance_returns_empty_balance_when_row_is_missing() -> None:
    warehouse = make_warehouse()
    interactor = build_get_interactor(warehouse, None)

    view = await interactor(GetBalanceQuery(warehouse.id, uuid4()))

    assert view.balance.quantity == Decimal(0)
    assert view.balance.total_value.kopecks == 0


async def test_list_balances_wraps_each_balance_in_view() -> None:
    warehouse = make_warehouse()
    nomenclature_id = uuid4()
    interactor = ListBalancesInteractor(
        identity_provider=FakeIdentityProvider(),
        warehouse_repository=FakeWarehouseRepository(warehouse),
        balance_repository=FakeStockBalanceRepository(
            make_balance(warehouse.id, nomenclature_id)
        ),
        staff_api=FakeStaffAPI(),
    )

    views = await interactor(ListBalancesQuery(warehouse.id))

    assert len(views) == 1
    assert isinstance(views[0], BalanceView)
    assert views[0].cost_visible is True
