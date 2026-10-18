from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.customer.domain.entities.customer import Customer
from myasnaya_derevnya.modules.customer.infrastructure.readers.customer.sqlalchemy import (
    SQLAlchemyCustomerReader,
)
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.sqlalchemy import (
    SQLAlchemyCustomerRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def _add_customer(
    session: AsyncSession,
    *,
    name: str,
    phone: str | None = None,
) -> Customer:
    customer = Customer.create(
        user_id=uuid4(), first_name=name, contact_phone=phone
    )
    await SQLAlchemyCustomerRepository(session).add(customer)

    return customer


async def test_search_matches_name_and_phone(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    phone = f"+7999{marker[:7]}"
    by_name = await _add_customer(db_session, name=f"{TEST_PREFIX}Данил {marker}")
    await _add_customer(db_session, name=f"{TEST_PREFIX}Другой {marker}")
    await _add_customer(db_session, name="Без маркера", phone=phone)
    await db_session.commit()

    reader = SQLAlchemyCustomerReader(db_session)

    by_name_items, by_name_total = await reader.list(
        search=f"данил {marker}", limit=10, offset=0
    )
    by_phone_items, by_phone_total = await reader.list(
        search=phone, limit=10, offset=0
    )

    assert by_name_total == 1
    assert [item.id for item in by_name_items] == [by_name.id]
    assert by_phone_total == 1
    assert [item.contact_phone for item in by_phone_items] == [phone]


async def test_search_escapes_wildcards(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    await _add_customer(db_session, name=f"{TEST_PREFIX}Скидка 50% {marker}")
    await _add_customer(db_session, name=f"{TEST_PREFIX}Без скидки {marker}")
    await db_session.commit()

    items, total = await SQLAlchemyCustomerReader(db_session).list(
        search=f"% {marker}", limit=10, offset=0
    )

    assert total == 1
    assert [item.first_name for item in items] == [f"{TEST_PREFIX}Скидка 50% {marker}"]


async def test_status_filter(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    active = await _add_customer(db_session, name=f"{TEST_PREFIX}Актив {marker}")
    blocked = await _add_customer(db_session, name=f"{TEST_PREFIX}Блок {marker}")
    await db_session.execute(
        text("update customer.customers set status = 'blocked' where id = :id"),
        {"id": blocked.id},
    )
    await db_session.commit()

    reader = SQLAlchemyCustomerReader(db_session)

    _blocked_items, blocked_total = await reader.list(
        search=marker, status="blocked", limit=10, offset=0
    )
    _active_items, active_total = await reader.list(
        search=marker, status="active", limit=10, offset=0
    )

    assert blocked_total == 1
    assert active_total == 1
    assert blocked.id != active.id


async def test_limit_offset_and_total(db_session: AsyncSession) -> None:
    marker = uuid4().hex[:6]
    for index in range(3):
        await _add_customer(db_session, name=f"{TEST_PREFIX}{marker}-{index}")
    await db_session.commit()

    reader = SQLAlchemyCustomerReader(db_session)

    first_page, total = await reader.list(search=marker, limit=2, offset=0)
    second_page, _ = await reader.list(search=marker, limit=2, offset=2)

    assert total == 3
    assert len(first_page) == 2
    assert len(second_page) == 1
    assert {item.id for item in first_page} & {item.id for item in second_page} == set()


async def test_get_returns_detail_or_none(db_session: AsyncSession) -> None:
    customer = await _add_customer(
        db_session, name=f"{TEST_PREFIX}Карточка {uuid4().hex[:6]}"
    )
    await db_session.commit()

    reader = SQLAlchemyCustomerReader(db_session)
    detail = await reader.get(customer.id)

    assert detail is not None
    assert detail.id == customer.id
    assert detail.first_name == customer.first_name
    assert detail.status == "active"
    assert await reader.get(uuid4()) is None
