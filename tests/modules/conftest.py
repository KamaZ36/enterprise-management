from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.connection import async_session_maker, engine
from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.main import create_app
from myasnaya_derevnya.modules.catalog.domain.entities.category import Category
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
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
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL недоступен: {exc}")

    async with async_session_maker() as session:
        yield session

    await clean_database()
    await engine.dispose()


@pytest.fixture
async def root_org_unit_id(db_session: AsyncSession) -> UUID:
    await bootstrap_system()

    root_id = await db_session.scalar(
        text("select id from business.org_units where parent_id is null limit 1")
    )
    assert root_id is not None

    return root_id


@pytest.fixture
async def make_nomenclature(db_session: AsyncSession) -> Callable[..., Coroutine]:
    categories = SQLAlchemyCategoryRepository(db_session)
    nomenclatures = SQLAlchemyNomenclatureRepository(db_session)
    created_categories: list[UUID] = []

    async def factory(
        name: str | None = None,
        sku: str | None = None,
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
            category_id=category_id,
        )
        await nomenclatures.add(nomenclature)
        await db_session.commit()

        return nomenclature

    return factory


@pytest.fixture
async def admin_session_id(db_session: AsyncSession) -> UUID:
    """Готовая сессия администратора для запросов через ASGI-клиент."""

    await bootstrap_system()

    user_id = await db_session.scalar(
        text(
            "select user_id from auth.user_identities"
            " where identity_type = 'username' and identifier = :identifier"
        ),
        {"identifier": settings.initial_admin_username},
    )

    session_id = uuid4()
    await db_session.execute(
        text(
            "insert into auth.user_sessions (id, user_id, expires_at, created_at)"
            " values (:id, :user_id, :expires_at, now())"
        ),
        {
            "id": session_id,
            "user_id": user_id,
            "expires_at": datetime.now(UTC) + timedelta(days=1),
        },
    )
    await db_session.commit()

    return session_id


@pytest.fixture
async def client(
    db_session: AsyncSession, admin_session_id: UUID
) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=create_app())

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_session_id}"},
    ) as api_client:
        yield api_client
