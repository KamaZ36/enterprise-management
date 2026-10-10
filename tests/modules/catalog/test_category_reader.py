"""Интеграционные тесты читателя категорий на настоящем PostgreSQL."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.category import Category
from myasnaya_derevnya.modules.catalog.infrastructure.readers.category.sqlalchemy import (
    SQLAlchemyCategoryReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.sqlalchemy import (
    SQLAlchemyCategoryRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def test_returns_ordered_and_keeps_parent(
    db_session: AsyncSession,
) -> None:
    marker = uuid4().hex[:6]
    categories = SQLAlchemyCategoryRepository(db_session)

    parent = Category.create(name=f"{TEST_PREFIX}Мясо {marker}", parent_id=None)
    await categories.add(parent)
    child = Category.create(name=f"{TEST_PREFIX}Говядина {marker}", parent_id=parent.id)
    await categories.add(child)
    await db_session.commit()

    items = await SQLAlchemyCategoryReader(db_session).list(search=marker)

    assert [item.name for item in items] == [
        f"{TEST_PREFIX}Говядина {marker}",
        f"{TEST_PREFIX}Мясо {marker}",
    ]
    assert items[0].parent_id == parent.id
    assert items[1].parent_id is None


async def test_search_is_case_insensitive_and_escapes_wildcards(
    db_session: AsyncSession,
) -> None:
    marker = uuid4().hex[:6]
    categories = SQLAlchemyCategoryRepository(db_session)

    await categories.add(
        Category.create(name=f"{TEST_PREFIX}Скидка 50% {marker}", parent_id=None)
    )
    await categories.add(
        Category.create(name=f"{TEST_PREFIX}Без скидки {marker}", parent_id=None)
    )
    await db_session.commit()

    reader = SQLAlchemyCategoryReader(db_session)

    upper = await reader.list(search=f"скидка 50% {marker}")
    literal = await reader.list(search=f"% {marker}")

    assert [item.name for item in upper] == [f"{TEST_PREFIX}Скидка 50% {marker}"]
    # Знак процента — литеральный символ: «любые символы» совпали бы с обеими
    assert [item.name for item in literal] == [f"{TEST_PREFIX}Скидка 50% {marker}"]


async def test_without_search_returns_categories(
    db_session: AsyncSession,
) -> None:
    marker = uuid4().hex[:6]
    categories = SQLAlchemyCategoryRepository(db_session)
    await categories.add(Category.create(name=f"{TEST_PREFIX}{marker}", parent_id=None))
    await db_session.commit()

    items = await SQLAlchemyCategoryReader(db_session).list()

    assert any(item.name == f"{TEST_PREFIX}{marker}" for item in items)
