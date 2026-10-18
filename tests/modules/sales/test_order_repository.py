from datetime import date
from decimal import Decimal
from uuid import uuid7

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.sales.domain.value_objects.fulfillment import (
    FulfillmentType,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_status import (
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.payment import (
    PaymentMethod,
    PaymentStatus,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.sqlalchemy import (
    SQLAlchemyOrderRepository,
)

pytestmark = pytest.mark.db


def make_order() -> Order:
    return Order.create(
        org_unit_id=uuid7(), channel=OrderChannel.POS, created_by=uuid7()
    )


async def test_order_round_trip_with_lines(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    order = make_order()
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal("1.5"), unit_price=45000)
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(2), unit_price=10000)

    await repository.add(order)
    loaded = await repository.get_by_id(order.id)

    assert loaded is not None
    assert loaded.status is OrderStatus.DRAFT
    assert loaded.channel is OrderChannel.POS
    assert len(loaded.lines) == 2
    assert loaded.total == 67500 + 20000


async def test_save_replaces_lines_and_status(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    order = make_order()
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=100)
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=200)
    await repository.add(order)

    order.revise([(uuid7(), Decimal(3), 500)])
    order.submit()
    order.set_status(OrderStatus.CONFIRMED)
    order.assign_number(7)
    await repository.save(order)

    loaded = await repository.get_by_id(order.id)

    assert loaded is not None
    assert len(loaded.lines) == 1
    assert loaded.total == 1500
    assert loaded.status is OrderStatus.CONFIRMED
    assert loaded.number == 7


async def test_numbers_go_per_point_and_day(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    point, other_point = uuid7(), uuid7()
    today, tomorrow = date(2026, 10, 14), date(2026, 10, 15)

    assert await repository.next_number(point, today) == 1
    assert await repository.next_number(point, today) == 2
    assert await repository.next_number(point, tomorrow) == 1
    assert await repository.next_number(other_point, today) == 1


async def test_unknown_order_returns_none(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)

    assert await repository.get_by_id(uuid7()) is None


async def test_payment_and_fulfillment_round_trip(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    order = Order.create(
        org_unit_id=uuid7(),
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=uuid7(),
    )
    order.set_fulfillment(FulfillmentType.DELIVERY, PaymentMethod.ON_DELIVERY)
    order.mark_paid(provider="manual", provider_id="ext-1")
    await repository.add(order)

    loaded = await repository.get_by_id(order.id)

    assert loaded is not None
    assert loaded.fulfillment_type is FulfillmentType.DELIVERY
    assert loaded.payment_method is PaymentMethod.ON_DELIVERY
    assert loaded.payment_status is PaymentStatus.PAID
    assert loaded.payment_provider == "manual"
    assert loaded.payment_provider_id == "ext-1"
    assert loaded.paid_at is not None


async def test_open_draft_is_found_by_customer_and_point(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    customer_id, point, other_point = uuid7(), uuid7(), uuid7()

    draft = Order.create(
        org_unit_id=point,
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=customer_id,
    )
    await repository.add(draft)

    assert await repository.get_open_draft(customer_id, point) is not None
    assert await repository.get_open_draft(customer_id, other_point) is None

    draft.submit()
    await repository.save(draft)

    assert await repository.get_open_draft(customer_id, point) is None


async def test_second_open_draft_is_rejected(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    customer_id, point = uuid7(), uuid7()

    first = Order.create(
        org_unit_id=point,
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=customer_id,
    )
    await repository.add(first)

    second = Order.create(
        org_unit_id=point,
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=customer_id,
    )

    with pytest.raises(IntegrityError):
        await repository.add(second)
