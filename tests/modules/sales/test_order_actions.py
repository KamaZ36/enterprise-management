from uuid import UUID, uuid7

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.sales.application.interactors.cancel_order import (
    CancelOrderCommand,
    CancelOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.confirm_order import (
    ConfirmOrderCommand,
    ConfirmOrderInteractor,
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


def build(
    *,
    user_id: UUID,
    staff: set[UUID] | None = None,
    profiles: dict[UUID, UUID] | None = None,
):
    repository = FakeOrderRepository()
    access = OrderAccess(
        staff_api=FakeStaffAPI(staff or set()),  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI(profiles or {}),  # type: ignore[arg-type]
    )
    transactions = FakeTransactionManager()
    identity = FakeIdentityProvider(user_id)

    confirm = ConfirmOrderInteractor(
        identity_provider=identity,  # type: ignore[arg-type]
        order_repository=repository,  # type: ignore[arg-type]
        order_access=access,
        transaction_manager=transactions,  # type: ignore[arg-type]
    )
    cancel = CancelOrderInteractor(
        identity_provider=identity,  # type: ignore[arg-type]
        order_repository=repository,  # type: ignore[arg-type]
        order_access=access,
        transaction_manager=transactions,  # type: ignore[arg-type]
    )

    return confirm, cancel, repository, transactions


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
    confirm, _, repository, transactions = build(user_id=staff_id, staff={staff_id})
    order = await make_order(repository, customer_id=uuid7())

    await confirm(ConfirmOrderCommand(order_id=order.id))

    saved = repository.orders[order.id]
    assert saved.status is OrderStatus.CONFIRMED
    assert saved.number == 1
    assert transactions.commits == 1


async def test_customer_confirms_own_order() -> None:
    user_id, customer_id = uuid7(), uuid7()
    confirm, _, repository, _ = build(user_id=user_id, profiles={user_id: customer_id})
    order = await make_order(repository, customer_id=customer_id)

    await confirm(ConfirmOrderCommand(order_id=order.id))

    assert repository.orders[order.id].status is OrderStatus.CONFIRMED


async def test_stranger_cannot_confirm_order() -> None:
    user_id = uuid7()
    confirm, _, repository, _ = build(user_id=user_id, profiles={user_id: uuid7()})
    order = await make_order(repository, customer_id=uuid7())

    with pytest.raises(ForbiddenError):
        await confirm(ConfirmOrderCommand(order_id=order.id))

    assert repository.orders[order.id].status is OrderStatus.DRAFT


async def test_confirming_twice_is_rejected() -> None:
    staff_id = uuid7()
    confirm, _, repository, _ = build(user_id=staff_id, staff={staff_id})
    order = await make_order(repository, customer_id=uuid7())
    await confirm(ConfirmOrderCommand(order_id=order.id))

    with pytest.raises(OrderStatusTransitionError):
        await confirm(ConfirmOrderCommand(order_id=order.id))


async def test_owner_cancels_own_draft() -> None:
    user_id, customer_id = uuid7(), uuid7()
    _, cancel, repository, _ = build(user_id=user_id, profiles={user_id: customer_id})
    order = await make_order(repository, customer_id=customer_id)

    await cancel(CancelOrderCommand(order_id=order.id))

    assert repository.orders[order.id].status is OrderStatus.CANCELLED


async def test_unknown_order_is_reported() -> None:
    staff_id = uuid7()
    confirm, _, _, _ = build(user_id=staff_id, staff={staff_id})

    with pytest.raises(OrderNotFoundError):
        await confirm(ConfirmOrderCommand(order_id=uuid7()))
