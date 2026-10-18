from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4, uuid7

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.sales.application.interactors.update_order import (
    UpdateOrderCommand,
    UpdateOrderInteractor,
    UpdateOrderLineCommand,
)
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.sales.domain.errors import (
    NotSoldAtPointError,
    OrderIsNotDraftError,
    OrderNotFoundError,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_status import (
    OrderStatus,
)

PLANNED_AT = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeStaffAPI:
    def __init__(self, allowed: set[UUID]) -> None:
        self._allowed = allowed

    async def can(self, *, user_id: UUID, permission: object, org_unit_id: UUID) -> bool:
        return user_id in self._allowed


class FakeCustomerAPI:
    async def get_customer_id(self, user_id: UUID) -> UUID | None:
        return None


class FakeCatalogAPI:
    def __init__(self, prices: dict[UUID, int]) -> None:
        self.prices = prices
        self.calls: list[tuple[UUID, list[UUID]]] = []

    async def prices_for_point(
        self, org_unit_id: UUID, nomenclature_ids: list[UUID]
    ) -> dict[UUID, int]:
        self.calls.append((org_unit_id, list(nomenclature_ids)))

        return {
            nid: self.prices[nid] for nid in nomenclature_ids if nid in self.prices
        }


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


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def build(
    *,
    user_id: UUID,
    staff: set[UUID] | None = None,
    prices: dict[UUID, int] | None = None,
):
    repository = FakeOrderRepository()
    catalog_api = FakeCatalogAPI(prices or {})
    transactions = FakeTransactionManager()
    access = OrderAccess(
        staff_api=FakeStaffAPI(staff or set()),  # type: ignore[arg-type]
        customer_api=FakeCustomerAPI(),  # type: ignore[arg-type]
    )
    interactor = UpdateOrderInteractor(
        identity_provider=FakeIdentityProvider(user_id),  # type: ignore[arg-type]
        order_repository=repository,  # type: ignore[arg-type]
        catalog_api=catalog_api,  # type: ignore[arg-type]
        order_access=access,
        transaction_manager=transactions,  # type: ignore[arg-type]
    )

    return interactor, repository, catalog_api, transactions


async def make_draft(repository: FakeOrderRepository) -> Order:
    order = Order.create(
        org_unit_id=uuid7(),
        channel=OrderChannel.POS,
        created_by=uuid7(),
    )
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=100)
    await repository.add(order)

    return order


async def test_staff_revises_draft_and_prices_come_from_point() -> None:
    staff_id = uuid7()
    first, second = uuid7(), uuid7()
    interactor, repository, catalog_api, transactions = build(
        user_id=staff_id, staff={staff_id}, prices={first: 1500, second: 2500}
    )
    order = await make_draft(repository)

    await interactor(
        UpdateOrderCommand(
            order_id=order.id,
            lines=(
                UpdateOrderLineCommand(nomenclature_id=first, quantity=Decimal(2)),
                UpdateOrderLineCommand(nomenclature_id=second, quantity=Decimal(1)),
            ),
            planned_at=PLANNED_AT,
            comment="без лука",
        )
    )

    saved = repository.orders[order.id]
    assert saved.status is OrderStatus.DRAFT
    assert saved.comment == "без лука"
    assert saved.planned_at == PLANNED_AT
    assert [(line.nomenclature_id, line.unit_price) for line in saved.lines] == [
        (first, 1500),
        (second, 2500),
    ]
    assert catalog_api.calls == [(order.org_unit_id, [first, second])]
    assert transactions.commits == 1


async def test_position_without_price_is_rejected() -> None:
    staff_id = uuid7()
    unknown = uuid7()
    interactor, repository, _, transactions = build(
        user_id=staff_id, staff={staff_id}, prices={}
    )
    order = await make_draft(repository)
    before = order.lines

    with pytest.raises(NotSoldAtPointError):
        await interactor(
            UpdateOrderCommand(
                order_id=order.id,
                lines=(
                    UpdateOrderLineCommand(
                        nomenclature_id=unknown, quantity=Decimal(1)
                    ),
                ),
            )
        )

    assert repository.orders[order.id].lines == before
    assert transactions.commits == 0


async def test_non_draft_cannot_be_edited() -> None:
    staff_id = uuid7()
    nomenclature_id = uuid7()
    interactor, repository, _, _ = build(
        user_id=staff_id, staff={staff_id}, prices={nomenclature_id: 1000}
    )
    order = await make_draft(repository)
    order.submit()
    await repository.save(order)

    with pytest.raises(OrderIsNotDraftError):
        await interactor(
            UpdateOrderCommand(
                order_id=order.id,
                lines=(
                    UpdateOrderLineCommand(
                        nomenclature_id=nomenclature_id, quantity=Decimal(1)
                    ),
                ),
            )
        )


async def test_customer_cannot_edit_order() -> None:
    user_id = uuid7()
    nomenclature_id = uuid7()
    interactor, repository, _, _ = build(
        user_id=user_id, prices={nomenclature_id: 1000}
    )
    order = await make_draft(repository)

    with pytest.raises(ForbiddenError):
        await interactor(
            UpdateOrderCommand(
                order_id=order.id,
                lines=(
                    UpdateOrderLineCommand(
                        nomenclature_id=nomenclature_id, quantity=Decimal(1)
                    ),
                ),
            )
        )


async def test_unknown_order_raises_not_found() -> None:
    staff_id = uuid7()
    interactor, _, _, _ = build(user_id=staff_id, staff={staff_id})

    with pytest.raises(OrderNotFoundError):
        await interactor(
            UpdateOrderCommand(order_id=uuid4(), lines=())
        )
