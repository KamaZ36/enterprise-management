from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.inventory.application.interactors.warehouses.update import (
    UpdateWarehouseCommand,
    UpdateWarehouseInteractor,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    WarehouseInUseError,
    WarehouseNotFoundError,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    async def get_root_unit_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        return self.allowed


class FakeWarehouseRepository:
    def __init__(self, warehouse: Warehouse | None) -> None:
        self.warehouse = warehouse
        self.saved: list[Warehouse] = []

    async def get_by_id(self, warehouse_id: UUID) -> Warehouse | None:
        return self.warehouse

    async def save(self, warehouse: Warehouse) -> None:
        self.saved.append(warehouse)


class FakeBalanceRepository:
    def __init__(self, has_stock: bool = False) -> None:
        self.has_stock = has_stock
        self.checked: list[UUID] = []

    async def has_any_for_warehouse(self, warehouse_id: UUID) -> bool:
        self.checked.append(warehouse_id)
        return self.has_stock


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_warehouse(type_: WarehouseType = WarehouseType.RAW) -> Warehouse:
    return Warehouse.create(
        org_unit_id=uuid4(), code="RAW-01", name="Склад сырья", type=type_
    )


def build(
    warehouse: Warehouse | None, *, allowed: bool = True, has_stock: bool = False
):
    repository = FakeWarehouseRepository(warehouse)
    balances = FakeBalanceRepository(has_stock=has_stock)
    transaction_manager = FakeTransactionManager()
    interactor = UpdateWarehouseInteractor(
        identity_provider=FakeIdentityProvider(),
        warehouse_repository=repository,
        balance_repository=balances,
        business_api=FakeBusinessAPI(),
        staff_api=FakeStaffAPI(allowed=allowed),
        transaction_manager=transaction_manager,
    )

    return interactor, repository, balances, transaction_manager


async def test_requires_manage_permission() -> None:
    warehouse = make_warehouse()
    interactor, repository, _, _ = build(warehouse, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(UpdateWarehouseCommand(warehouse_id=warehouse.id))

    assert repository.saved == []


async def test_unknown_warehouse_raises_not_found() -> None:
    interactor, _, _, _ = build(None)

    with pytest.raises(WarehouseNotFoundError):
        await interactor(UpdateWarehouseCommand(warehouse_id=uuid4()))


async def test_rename_and_deactivate() -> None:
    warehouse = make_warehouse()
    interactor, repository, balances, transaction_manager = build(warehouse)

    await interactor(
        UpdateWarehouseCommand(
            warehouse_id=warehouse.id, name="Склад сырья №1", is_active=False
        )
    )

    assert warehouse.name == "Склад сырья №1"
    assert warehouse.is_active is False
    assert repository.saved == [warehouse]
    assert transaction_manager.commits == 1
    assert balances.checked == []


async def test_type_cannot_change_with_stock() -> None:
    warehouse = make_warehouse()
    interactor, repository, balances, _ = build(warehouse, has_stock=True)

    with pytest.raises(WarehouseInUseError):
        await interactor(
            UpdateWarehouseCommand(
                warehouse_id=warehouse.id, type_=WarehouseType.FINISHED
            )
        )

    assert warehouse.type is WarehouseType.RAW
    assert repository.saved == []
    assert balances.checked == [warehouse.id]


async def test_type_changes_while_warehouse_is_empty() -> None:
    warehouse = make_warehouse()
    interactor, repository, _, _ = build(warehouse, has_stock=False)

    await interactor(
        UpdateWarehouseCommand(warehouse_id=warehouse.id, type_=WarehouseType.FINISHED)
    )

    assert warehouse.type is WarehouseType.FINISHED
    assert repository.saved == [warehouse]


async def test_activate_returns_warehouse_to_work() -> None:
    warehouse = make_warehouse()
    warehouse.deactivate()
    interactor, _, _, _ = build(warehouse)

    await interactor(UpdateWarehouseCommand(warehouse_id=warehouse.id, is_active=True))

    assert warehouse.is_active is True
