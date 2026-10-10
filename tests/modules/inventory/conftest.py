"""Фикстуры тестов складского модуля."""

from collections.abc import Callable, Coroutine
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.sqlalchemy import (
    SQLAlchemyWarehouseRepository,
)
from tests.modules.helpers import TEST_PREFIX


@pytest.fixture
async def make_warehouse(db_session: AsyncSession) -> Callable[..., Coroutine]:
    repository = SQLAlchemyWarehouseRepository(db_session)

    async def factory(
        type_: WarehouseType = WarehouseType.RAW, org_unit_id: UUID | None = None
    ) -> Warehouse:
        warehouse = Warehouse.create(
            org_unit_id=org_unit_id or uuid4(),
            code=f"{TEST_PREFIX}{uuid4().hex[:8]}",
            name="Склад",
            type=type_,
        )
        await repository.add(warehouse)
        await db_session.commit()

        return warehouse

    return factory
