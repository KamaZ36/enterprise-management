from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
)
from myasnaya_derevnya.modules.production.domain.entities.tech_card import (
    TechCard,
    TechCardLine,
)
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.production_order.sqlalchemy import (
    SQLAlchemyProductionOrderReader,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.tech_card.sqlalchemy import (
    SQLAlchemyTechCardReader,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.sqlalchemy import (
    SQLAlchemyProductionOrderRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.sqlalchemy import (
    SQLAlchemyTechCardRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def make_card(*, code: str, version: int = 1) -> TechCard:
    lines = [
        TechCardLine.component(nomenclature_id=uuid4(), quantity=Decimal(100)),
        TechCardLine.output(
            nomenclature_id=uuid4(),
            quantity=Decimal(80),
            output_kind=OutputKind.MAIN,
        ),
    ]

    return TechCard.create(
        code=code,
        name="Копчение",
        basis=TechCardBasis.INPUT,
        lines=lines,
        version=version,
    )


async def test_tech_card_reader_search_order_and_line_count(
    db_session: AsyncSession,
) -> None:
    marker = uuid4().hex[:6]
    repository = SQLAlchemyTechCardRepository(db_session)
    reader = SQLAlchemyTechCardReader(db_session)

    await repository.add(
        make_card(code=f"{TEST_PREFIX}A-{marker}", version=1)
    )
    await repository.add(
        make_card(code=f"{TEST_PREFIX}A-{marker}", version=2)
    )
    await repository.add(make_card(code=f"{TEST_PREFIX}B-{marker}", version=1))
    await db_session.commit()

    items, total = await reader.list(search=marker, limit=10, offset=0)

    assert total == 3
    assert [(item.code, item.version) for item in items] == [
        (f"{TEST_PREFIX}A-{marker}", 2),
        (f"{TEST_PREFIX}A-{marker}", 1),
        (f"{TEST_PREFIX}B-{marker}", 1),
    ]
    assert all(item.line_count == 2 for item in items)


async def test_tech_card_reader_searches_by_name(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    repository = SQLAlchemyTechCardRepository(db_session)
    card = make_card(code=f"{TEST_PREFIX}NAME-{marker}")
    await repository.add(card)
    await db_session.commit()

    reader = SQLAlchemyTechCardReader(db_session)

    by_code, code_total = await reader.list(search=f"name-{marker}", limit=10, offset=0)
    by_name, name_total = await reader.list(search="копчение", limit=10, offset=0)

    assert code_total == 1
    assert [item.id for item in by_code] == [card.id]
    assert name_total >= 1
    assert card.id in {item.id for item in by_name}


async def test_tech_card_reader_pagination(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    repository = SQLAlchemyTechCardRepository(db_session)
    for index in range(3):
        await repository.add(make_card(code=f"{TEST_PREFIX}P-{marker}-{index}"))
    await db_session.commit()

    reader = SQLAlchemyTechCardReader(db_session)
    first, total = await reader.list(search=marker, limit=2, offset=0)
    second, _ = await reader.list(search=marker, limit=2, offset=2)

    assert total == 3
    assert len(first) == 2
    assert len(second) == 1
    assert {item.id for item in first} & {item.id for item in second} == set()


async def test_order_reader_filters_and_order(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    cards = SQLAlchemyTechCardRepository(db_session)
    orders = SQLAlchemyProductionOrderRepository(db_session)
    card = make_card(code=f"{TEST_PREFIX}ORD-{marker}")
    await cards.add(card)

    point_a, point_b = uuid4(), uuid4()

    def order(org_unit_id, offset_minutes: int) -> ProductionOrder:
        return ProductionOrder.create(
            org_unit_id=org_unit_id,
            tech_card=card,
            batch_count=Decimal(1),
            occurred_at=BASE_TIME + timedelta(minutes=offset_minutes),
        )

    draft = order(point_a, 0)
    cancelled = order(point_a, 10)
    cancelled.cancel()
    other_point = order(point_b, 20)

    for item in (draft, cancelled, other_point):
        await orders.add(item)
    await db_session.commit()

    reader = SQLAlchemyProductionOrderReader(db_session)

    at_point, point_total = await reader.list(
        org_unit_ids=[point_a],
        statuses=None,
        occurred_from=None,
        occurred_to=None,
        limit=10,
        offset=0,
    )
    cancelled_only, cancelled_total = await reader.list(
        org_unit_ids=None,
        statuses=[ProductionOrderStatus.CANCELLED.value],
        occurred_from=None,
        occurred_to=None,
        limit=10,
        offset=0,
    )
    window, window_total = await reader.list(
        org_unit_ids=None,
        statuses=None,
        occurred_from=BASE_TIME + timedelta(minutes=5),
        occurred_to=BASE_TIME + timedelta(minutes=15),
        limit=10,
        offset=0,
    )

    assert point_total == 2
    assert [item.id for item in at_point] == [cancelled.id, draft.id]
    assert cancelled_total == 1
    assert [item.id for item in cancelled_only] == [cancelled.id]
    assert window_total == 1
    assert [item.id for item in window] == [cancelled.id]


async def test_order_reader_pagination(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    cards = SQLAlchemyTechCardRepository(db_session)
    orders = SQLAlchemyProductionOrderRepository(db_session)
    card = make_card(code=f"{TEST_PREFIX}PAGE-{marker}")
    await cards.add(card)
    point = uuid4()

    created = []
    for index in range(3):
        item = ProductionOrder.create(
            org_unit_id=point,
            tech_card=card,
            batch_count=Decimal(1),
            occurred_at=BASE_TIME + timedelta(minutes=index),
        )
        await orders.add(item)
        created.append(item)
    await db_session.commit()

    reader = SQLAlchemyProductionOrderReader(db_session)
    first, total = await reader.list(
        org_unit_ids=[point],
        statuses=None,
        occurred_from=None,
        occurred_to=None,
        limit=2,
        offset=0,
    )
    second, _ = await reader.list(
        org_unit_ids=[point],
        statuses=None,
        occurred_from=None,
        occurred_to=None,
        limit=2,
        offset=2,
    )

    assert total == 3
    assert [item.id for item in first] == [created[2].id, created[1].id]
    assert [item.id for item in second] == [created[0].id]
