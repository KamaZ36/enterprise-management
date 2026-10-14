from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid7

import pytest

from myasnaya_derevnya.modules.sales.domain.entities.order import (
    Order,
    OrderChannel,
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.domain.errors import (
    EmptyOrderLineError,
    NegativePriceError,
    OrderAlreadyClosedError,
    OrderIsNotDraftError,
    OrderStatusTransitionError,
    TimezoneRequiredError,
)


def make_order() -> Order:
    return Order.create(
        org_unit_id=uuid7(),
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=uuid7(),
    )


def test_new_order_is_draft_and_empty() -> None:
    order = make_order()

    assert order.status is OrderStatus.DRAFT
    assert order.lines == []
    assert order.total == 0
    assert order.is_editable
    assert order.created_at.tzinfo == UTC


def test_line_total_and_order_total() -> None:
    order = make_order()
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal("1.5"), unit_price=45000)
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(2), unit_price=10000)

    assert order.total == 67500 + 20000


def test_quantity_and_price_are_validated() -> None:
    order = make_order()

    with pytest.raises(EmptyOrderLineError):
        order.add_line(nomenclature_id=uuid7(), quantity=Decimal(0), unit_price=100)

    with pytest.raises(NegativePriceError):
        order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=-1)


def test_naive_planned_time_is_rejected() -> None:
    with pytest.raises(TimezoneRequiredError):
        Order.create(
            org_unit_id=uuid7(),
            channel=OrderChannel.PHONE,
            created_by=uuid7(),
            planned_at=datetime(2026, 10, 14, 18, 0),
        )


def test_confirmed_order_cannot_be_edited() -> None:
    order = make_order()
    order.set_status(OrderStatus.CONFIRMED)

    assert not order.is_editable

    with pytest.raises(OrderIsNotDraftError):
        order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=100)


def test_revise_replaces_lines() -> None:
    order = make_order()
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=100)
    order.revise([(uuid7(), Decimal(2), 300), (uuid7(), Decimal(1), 500)])

    assert len(order.lines) == 2
    assert order.total == 1100


def test_statuses_move_only_forward() -> None:
    order = make_order()

    with pytest.raises(OrderStatusTransitionError):
        order.set_status(OrderStatus.COMPLETED)

    for status in (
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.COMPLETED,
    ):
        order.set_status(status)

    assert order.status is OrderStatus.COMPLETED
    assert order.completed_at is not None

    with pytest.raises(OrderStatusTransitionError):
        order.set_status(OrderStatus.PREPARING)


def test_completed_order_cannot_be_cancelled() -> None:
    order = make_order()
    for status in (
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
        OrderStatus.READY,
        OrderStatus.COMPLETED,
    ):
        order.set_status(status)

    with pytest.raises(OrderAlreadyClosedError):
        order.cancel()


def test_cancel_marks_time() -> None:
    order = make_order()
    order.cancel()

    assert order.status is OrderStatus.CANCELLED
    assert order.cancelled_at is not None


def test_line_keeps_price_copy() -> None:
    order = make_order()
    line = order.add_line(
        nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=45000
    )

    assert line.unit_price == 45000
