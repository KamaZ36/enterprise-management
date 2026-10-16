from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID, uuid7

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.sales.application.interactors.cancel_order import (
    CancelOrderCommand,
    CancelOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.complete_order import (
    CompleteOrderCommand,
    CompleteOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.confirm_order import (
    ConfirmOrderCommand,
    ConfirmOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.mark_order_ready import (
    MarkOrderReadyCommand,
    MarkOrderReadyInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.start_preparing_order import (
    StartPreparingOrderCommand,
    StartPreparingOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.domain.entities.order import (
    Order,
    OrderChannel,
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.domain.errors import (
    OrderNotFoundError,
    OrderStatusTransitionError,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeStaffAPI:
    def __init__(self, allowed: set[UUID]) -> None:
        self._allowed = allowed

    async def can(
        self, *, user_id: UUID, permission: object, org_unit_id: UUID
    ) -> bool:
        return user_id in self._allowed


class FakeCustomerAPI:
    def __init__(self, profiles: dict[UUID, UUID]) -> None:
        self._profiles = profiles

    async def get_customer_id(self, user_id: UUID) -> UUID | None:
        return self._profiles.get(user_id)


class FakeOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[UUID, Order] = {}
        self.saved = 0

    async def add(self, order: Order) -> None:
        self.orders[order.id] = order

    async def save(self, order: Order) -> None:
        self.orders[order.id] = order
        self.saved += 1

    async def get_by_id(self, order_id: UUID) -> Order | None:
        return self.orders.get(order_id)

    async def next_number(self, org_unit_id: UUID, day: object) -> int:
        return 1


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


@dataclass(frozen=True, slots=True)
class FakeWarehouse:
    id: UUID


class FakeInventoryAPI:
    def __init__(
        self, warehouse: FakeWarehouse | None = None, costs: list[int] | None = None
    ) -> None:
        self._warehouse = warehouse
        self._costs = costs or []
        self.sales: list[dict[str, object]] = []

    async def default_sales_warehouse(self, org_unit_id: UUID) -> FakeWarehouse | None:
        return self._warehouse

    async def post_sale(
        self,
        *,
        document_id: UUID,
        warehouse_id: UUID,
        occurred_at: object,
        lines: list[object],
        posted_by: UUID | None = None,
    ) -> tuple[int, ...]:
        self.sales.append(
            {
                "document_id": document_id,
                "warehouse_id": warehouse_id,
                "lines": list(lines),
                "posted_by": posted_by,
            }
        )

        return tuple(self._costs)


@dataclass(frozen=True, slots=True)
class OrderActions:
    confirm: ConfirmOrderInteractor
    cancel: CancelOrderInteractor
    preparing: StartPreparingOrderInteractor
    ready: MarkOrderReadyInteractor
    complete: CompleteOrderInteractor
    repository: FakeOrderRepository
    transactions: FakeTransactionManager
    inventory: FakeInventoryAPI


def build(
    *,
    user_id: UUID,
    staff: set[UUID] | None = None,
    profiles: dict[UUID, UUID] | None = None,
    inventory: FakeInventoryAPI | None = None,
) -> OrderActions:
    repository = FakeOrderRepository()
    access = OrderAccess(
        staff_api=FakeStaffAPI(staff or set()),  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI(profiles or {}),  # type: ignore[arg-type]
    )
    transactions = FakeTransactionManager()
    identity = FakeIdentityProvider(user_id)
    inventory_api = inventory or FakeInventoryAPI()

    return OrderActions(
        confirm=ConfirmOrderInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            order_access=access,
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
        cancel=CancelOrderInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            order_access=access,
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
        preparing=StartPreparingOrderInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            order_access=access,
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
        ready=MarkOrderReadyInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            order_access=access,
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
        complete=CompleteOrderInteractor(
            identity_provider=identity,  # type: ignore[arg-type]
            order_repository=repository,  # type: ignore[arg-type]
            order_access=access,
            inventory_api=inventory_api,  # type: ignore[arg-type]
            transaction_manager=transactions,  # type: ignore[arg-type]
        ),
        repository=repository,
        transactions=transactions,
        inventory=inventory_api,
    )


async def make_order(
    repository: FakeOrderRepository, customer_id: UUID | None
) -> Order:
    order = Order.create(
        org_unit_id=uuid7(),
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=customer_id,
    )
    await repository.add(order)

    return order


async def test_staff_confirms_order_and_number_is_assigned() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())

    await actions.confirm(ConfirmOrderCommand(order_id=order.id))

    saved = actions.repository.orders[order.id]
    assert saved.status is OrderStatus.CONFIRMED
    assert saved.number == 1
    assert actions.transactions.commits == 1


async def test_customer_confirms_own_order() -> None:
    user_id, customer_id = uuid7(), uuid7()
    actions = build(user_id=user_id, profiles={user_id: customer_id})
    order = await make_order(actions.repository, customer_id=customer_id)

    await actions.confirm(ConfirmOrderCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.CONFIRMED


async def test_stranger_cannot_confirm_order() -> None:
    user_id = uuid7()
    actions = build(user_id=user_id, profiles={user_id: uuid7()})
    order = await make_order(actions.repository, customer_id=uuid7())

    with pytest.raises(ForbiddenError):
        await actions.confirm(ConfirmOrderCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.DRAFT


async def test_confirming_twice_is_rejected() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())
    await actions.confirm(ConfirmOrderCommand(order_id=order.id))

    with pytest.raises(OrderStatusTransitionError):
        await actions.confirm(ConfirmOrderCommand(order_id=order.id))


async def test_owner_cancels_own_draft() -> None:
    user_id, customer_id = uuid7(), uuid7()
    actions = build(user_id=user_id, profiles={user_id: customer_id})
    order = await make_order(actions.repository, customer_id=customer_id)

    await actions.cancel(CancelOrderCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.CANCELLED


async def test_unknown_order_is_reported() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})

    with pytest.raises(OrderNotFoundError):
        await actions.confirm(ConfirmOrderCommand(order_id=uuid7()))


async def test_staff_moves_confirmed_order_to_preparing() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())
    await actions.confirm(ConfirmOrderCommand(order_id=order.id))

    await actions.preparing(StartPreparingOrderCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.PREPARING


async def test_customer_cannot_start_preparing() -> None:
    user_id, customer_id = uuid7(), uuid7()
    actions = build(user_id=user_id, profiles={user_id: customer_id})
    order = await make_order(actions.repository, customer_id=customer_id)
    await actions.confirm(ConfirmOrderCommand(order_id=order.id))

    with pytest.raises(ForbiddenError):
        await actions.preparing(StartPreparingOrderCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.CONFIRMED


async def test_staff_marks_preparing_order_ready() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())
    order.set_status(OrderStatus.CONFIRMED)
    order.set_status(OrderStatus.PREPARING)
    await actions.repository.save(order)

    await actions.ready(MarkOrderReadyCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.READY


async def test_cannot_start_preparing_a_draft() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())

    with pytest.raises(OrderStatusTransitionError):
        await actions.preparing(StartPreparingOrderCommand(order_id=order.id))


async def test_staff_completes_ready_order() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())
    order.set_status(OrderStatus.CONFIRMED)
    order.set_status(OrderStatus.PREPARING)
    order.set_status(OrderStatus.READY)
    await actions.repository.save(order)

    await actions.complete(CompleteOrderCommand(order_id=order.id))

    saved = actions.repository.orders[order.id]
    assert saved.status is OrderStatus.COMPLETED
    assert saved.completed_at is not None


async def test_customer_cannot_complete_order() -> None:
    user_id, customer_id = uuid7(), uuid7()
    actions = build(user_id=user_id, profiles={user_id: customer_id})
    order = await make_order(actions.repository, customer_id=customer_id)
    order.set_status(OrderStatus.CONFIRMED)
    order.set_status(OrderStatus.PREPARING)
    order.set_status(OrderStatus.READY)
    await actions.repository.save(order)

    with pytest.raises(ForbiddenError):
        await actions.complete(CompleteOrderCommand(order_id=order.id))

    assert actions.repository.orders[order.id].status is OrderStatus.READY


async def test_cannot_complete_a_draft() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())

    with pytest.raises(OrderStatusTransitionError):
        await actions.complete(CompleteOrderCommand(order_id=order.id))


async def test_completing_order_writes_off_stock_and_records_costs() -> None:
    staff_id = uuid7()
    warehouse = FakeWarehouse(id=uuid7())
    inventory = FakeInventoryAPI(warehouse=warehouse, costs=[12_000])
    actions = build(user_id=staff_id, staff={staff_id}, inventory=inventory)
    order = await make_order(actions.repository, customer_id=uuid7())
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(2), unit_price=10_000)
    order.set_status(OrderStatus.CONFIRMED)
    order.set_status(OrderStatus.PREPARING)
    order.set_status(OrderStatus.READY)
    await actions.repository.save(order)

    await actions.complete(CompleteOrderCommand(order_id=order.id))

    saved = actions.repository.orders[order.id]
    assert saved.status is OrderStatus.COMPLETED
    assert saved.warehouse_id == warehouse.id
    assert saved.lines[0].cost_kopecks == 12_000
    assert saved.lines[0].margin == 20_000 - 12_000
    assert inventory.sales[0]["warehouse_id"] == warehouse.id


async def test_completing_order_without_warehouse_skips_write_off() -> None:
    staff_id = uuid7()
    actions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(actions.repository, customer_id=uuid7())
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=10_000)
    order.set_status(OrderStatus.CONFIRMED)
    order.set_status(OrderStatus.PREPARING)
    order.set_status(OrderStatus.READY)
    await actions.repository.save(order)

    await actions.complete(CompleteOrderCommand(order_id=order.id))

    saved = actions.repository.orders[order.id]
    assert saved.status is OrderStatus.COMPLETED
    assert saved.warehouse_id is None
    assert saved.lines[0].cost_kopecks is None
    assert actions.inventory.sales == []
