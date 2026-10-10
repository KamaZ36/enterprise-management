"""Интеграционные тесты читателя номенклатуры на настоящем PostgreSQL."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.category import Category
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
)
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.sqlalchemy import (
    SQLAlchemyCategoryRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


def reader(session: AsyncSession) -> SQLAlchemyNomenclatureReader:
    return SQLAlchemyNomenclatureReader(session)


async def test_returns_dto_with_category_name(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    categories = SQLAlchemyCategoryRepository(db_session)
    category = Category.create(name=f"{TEST_PREFIX}Мясо {marker}", parent_id=None)
    await categories.add(category)

    await make_nomenclature(
        name=f"Говядина {marker}",
        sku=f"{TEST_PREFIX}{marker}-1",
        category_id=category.id,
    )

    items, total = await reader(db_session).list(search=marker, limit=50)

    assert total == 1
    assert items[0].name == f"Говядина {marker}"
    assert items[0].category_name == f"{TEST_PREFIX}Мясо {marker}"
    # Читатель отдаёт плоские данные, а не доменную сущность
    assert not hasattr(items[0], "created_at")


async def test_search_matches_name_case_insensitively(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    await make_nomenclature(name=f"Говядина {marker}", sku=f"{TEST_PREFIX}{marker}-1")
    await make_nomenclature(name=f"Свинина {marker}", sku=f"{TEST_PREFIX}{marker}-2")

    items, total = await reader(db_session).list(search=f"ГОВЯДИНА {marker}", limit=50)

    assert total == 1
    assert items[0].name.startswith("Говядина")


async def test_search_matches_sku(db_session: AsyncSession, make_nomenclature) -> None:
    marker = uuid4().hex[:6]
    await make_nomenclature(name=f"Товар {marker}", sku=f"{TEST_PREFIX}{marker}-777")

    items, total = await reader(db_session).list(search=f"{marker}-777", limit=50)

    assert total == 1
    assert items[0].sku.endswith("-777")


async def test_search_treats_percent_as_literal(
    db_session: AsyncSession, make_nomenclature
) -> None:
    """Знак процента в поиске — это символ, а не «любые символы».

    Без экранирования шаблон «% marker» совпал бы с обеими позициями.
    """
    marker = uuid4().hex[:6]
    await make_nomenclature(name=f"Скидка 50% {marker}", sku=f"{TEST_PREFIX}{marker}-1")
    await make_nomenclature(name=f"Без скидки {marker}", sku=f"{TEST_PREFIX}{marker}-2")

    items, total = await reader(db_session).list(search=f"% {marker}", limit=50)

    assert total == 1
    assert "50%" in items[0].name


async def test_filters_by_type_and_category(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    categories = SQLAlchemyCategoryRepository(db_session)
    category = Category.create(name=f"{TEST_PREFIX}{marker}", parent_id=None)
    await categories.add(category)

    other_category = Category.create(
        name=f"{TEST_PREFIX}{marker}-other", parent_id=None
    )
    await categories.add(other_category)

    await make_nomenclature(
        name=f"Сырьё {marker}",
        sku=f"{TEST_PREFIX}{marker}-1",
        type_=NomenclatureType.RAW_MATERIAL,
        category_id=category.id,
    )
    await make_nomenclature(
        name=f"Готовое {marker}",
        sku=f"{TEST_PREFIX}{marker}-2",
        type_=NomenclatureType.FINISHED_GOOD,
        category_id=category.id,
    )
    await make_nomenclature(
        name=f"Чужое {marker}",
        sku=f"{TEST_PREFIX}{marker}-3",
        type_=NomenclatureType.RAW_MATERIAL,
        category_id=other_category.id,
    )

    only_raw, raw_total = await reader(db_session).list(
        search=marker, type_code=NomenclatureType.RAW_MATERIAL.value, limit=50
    )
    only_category, category_total = await reader(db_session).list(
        search=marker, category_id=category.id, limit=50
    )

    assert raw_total == 2
    assert {item.sku for item in only_raw} == {
        f"{TEST_PREFIX}{marker}-1",
        f"{TEST_PREFIX}{marker}-3",
    }
    assert category_total == 2
    assert {item.sku for item in only_category} == {
        f"{TEST_PREFIX}{marker}-1",
        f"{TEST_PREFIX}{marker}-2",
    }


async def test_pagination_returns_total_and_ordered_window(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    for number in range(3):
        await make_nomenclature(
            name=f"Позиция {number} {marker}",
            sku=f"{TEST_PREFIX}{marker}-{number}",
        )

    first_page, total = await reader(db_session).list(search=marker, limit=2, offset=0)
    second_page, _ = await reader(db_session).list(search=marker, limit=2, offset=2)

    assert total == 3
    assert [item.name for item in first_page] == [
        f"Позиция 0 {marker}",
        f"Позиция 1 {marker}",
    ]
    assert [item.name for item in second_page] == [f"Позиция 2 {marker}"]


async def test_unknown_category_returns_empty(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    await make_nomenclature(name=f"Позиция {marker}", sku=f"{TEST_PREFIX}{marker}-1")

    items, total = await reader(db_session).list(
        search=marker, category_id=UUID(int=0), limit=50
    )

    assert (items, total) == ([], 0)
