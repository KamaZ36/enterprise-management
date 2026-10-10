"""Фикстуры интеграционных тестов: настоящая база и фабрики справочников.

Отдельная БД `myasnaya_derevnya_test` задаётся в tests/conftest.py.
"""

from collections.abc import AsyncIterator, Callable, Coroutine
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.connection import async_session_maker, engine
from myasnaya_derevnya.modules.catalog.domain.entities.category import Category
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.category.sqlalchemy import (
    SQLAlchemyCategoryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from tests.modules.helpers import TEST_PREFIX, clean_database


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    try:
        async with async_session_maker() as probe:
            await probe.execute(text("select 1"))
    except Exception as exc:  # noqa: BLE001 - любая причина недоступности БД
        pytest.skip(f"PostgreSQL недоступен: {exc}")

    async with async_session_maker() as session:
        yield session

    await clean_database()
    # Каждый тест получает свой event loop, поэтому пул соединений нельзя
    # оставлять живым до следующего теста.
    await engine.dispose()


@pytest.fixture
async def make_nomenclature(db_session: AsyncSession) -> Callable[..., Coroutine]:
    """Создаёт номенклатуру. Имя и SKU можно задать, иначе они уникальны."""

    categories = SQLAlchemyCategoryRepository(db_session)
    nomenclatures = SQLAlchemyNomenclatureRepository(db_session)
    created_categories: list[UUID] = []

    async def factory(
        name: str | None = None,
        sku: str | None = None,
        type_: NomenclatureType = NomenclatureType.RAW_MATERIAL,
        unit: UnitOfMeasurement = UnitOfMeasurement.KG,
        category_id: UUID | None = None,
    ) -> Nomenclature:
        if category_id is None:
            category = Category.create(
                name=f"{TEST_PREFIX}{uuid4().hex[:8]}", parent_id=None
            )
            await categories.add(category)
            created_categories.append(category.id)
            category_id = category.id

        nomenclature = Nomenclature.create(
            sku=sku or f"{TEST_PREFIX}{uuid4().hex[:8]}",
            name=name or "Тестовая номенклатура",
            unit=unit,
            type_=type_,
            category_id=category_id,
        )
        await nomenclatures.add(nomenclature)
        await db_session.commit()

        return nomenclature

    return factory
