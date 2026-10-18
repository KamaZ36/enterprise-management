from decimal import Decimal
from uuid import uuid7

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.sales.domain.entities.order import Order
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)
from myasnaya_derevnya.modules.sales.infrastructure.readers.order.sqlalchemy import (
    SQLAlchemyOrderReader,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.sqlalchemy import (
    SQLAlchemyOrderRepository,
)

pytestmark = pytest.mark.db


async def test_list_filters_and_totals(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    reader = SQLAlchemyOrderReader(db_session)

    point, other_point = uuid7(), uuid7()
    customer_id = uuid7()

    first = Order.create(
        org_unit_id=point, channel=OrderChannel.POS, created_by=uuid7()
    )
    first.add_line(nomenclature_id=uuid7(), quantity=Decimal(2), unit_price=5000)

    second = Order.create(
        org_unit_id=point,
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=customer_id,
    )
    second.add_line(nomenclature_id=uuid7(), quantity=Decimal("1.5"), unit_price=10000)

    third = Order.create(
        org_unit_id=other_point, channel=OrderChannel.POS, created_by=uuid7()
    )

    for order in (first, second, third):
        await repository.add(order)

    items, total = await reader.list(org_unit_ids=[point], limit=10, offset=0)

    assert total == 2
    assert {item.id for item in items} == {first.id, second.id}
    assert {item.total for item in items} == {10000, 15000}

    by_lines = {item.id: item.line_count for item in items}
    assert by_lines[first.id] == 1
    assert third.id not in by_lines

    only_customer, customer_total = await reader.list(customer_id=customer_id)

    assert customer_total == 1
    assert only_customer[0].id == second.id
    assert only_customer[0].number is None

    _same_day, day_total = await reader.list(day=first.created_at.date())

    assert day_total == 3

    _drafts, draft_total = await reader.list(statuses=["draft"])

    assert draft_total == 3

    nothing, nothing_total = await reader.list(statuses=["completed"])

    assert nothing == []
    assert nothing_total == 0


async def test_detail_returns_lines_and_total(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOrderRepository(db_session)
    reader = SQLAlchemyOrderReader(db_session)

    order = Order.create(
        org_unit_id=uuid7(),
        channel=OrderChannel.SITE,
        created_by=uuid7(),
        customer_id=uuid7(),
        comment="без лука",
    )
    nomenclature_id = uuid7()
    order.add_line(
        nomenclature_id=nomenclature_id, quantity=Decimal(3), unit_price=7000
    )
    order.add_line(nomenclature_id=uuid7(), quantity=Decimal(1), unit_price=1000)
    await repository.add(order)

    detail = await reader.get(order.id)

    assert detail is not None
    assert detail.comment == "без лука"
    assert len(detail.lines) == 2
    assert detail.total == 22000
    assert detail.lines[0].nomenclature_id == nomenclature_id
    assert detail.lines[0].nomenclature_name is None


async def test_detail_of_unknown_order_is_none(db_session: AsyncSession) -> None:
    reader = SQLAlchemyOrderReader(db_session)

    assert await reader.get(uuid7()) is None
