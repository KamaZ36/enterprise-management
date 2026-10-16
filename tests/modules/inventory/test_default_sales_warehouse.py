from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    WarehouseType,
)
from tests.modules.inventory.helpers import build_inventory_api

pytestmark = pytest.mark.db


async def test_prefers_shop_warehouse_for_the_point(
    db_session: AsyncSession, make_warehouse
) -> None:
    org_unit_id = uuid4()
    raw = await make_warehouse(type_=WarehouseType.RAW, org_unit_id=org_unit_id)
    shop = await make_warehouse(type_=WarehouseType.SHOP, org_unit_id=org_unit_id)

    api = build_inventory_api(db_session)
    resolved = await api.default_sales_warehouse(org_unit_id)

    assert resolved is not None
    assert resolved.id == shop.id
    assert resolved.id != raw.id


async def test_falls_back_to_finished_warehouse(
    db_session: AsyncSession, make_warehouse
) -> None:
    org_unit_id = uuid4()
    await make_warehouse(type_=WarehouseType.RAW, org_unit_id=org_unit_id)
    finished = await make_warehouse(
        type_=WarehouseType.FINISHED, org_unit_id=org_unit_id
    )

    api = build_inventory_api(db_session)
    resolved = await api.default_sales_warehouse(org_unit_id)

    assert resolved is not None
    assert resolved.id == finished.id


async def test_ignores_other_points(
    db_session: AsyncSession, make_warehouse
) -> None:
    await make_warehouse(type_=WarehouseType.SHOP, org_unit_id=uuid4())
    other = uuid4()
    raw = await make_warehouse(type_=WarehouseType.RAW, org_unit_id=other)

    api = build_inventory_api(db_session)
    resolved = await api.default_sales_warehouse(other)

    assert resolved is None
    assert raw is not None


async def test_returns_none_when_no_sales_warehouse(
    db_session: AsyncSession, make_warehouse
) -> None:
    org_unit_id: UUID = uuid4()
    await make_warehouse(type_=WarehouseType.RAW, org_unit_id=org_unit_id)

    api = build_inventory_api(db_session)

    assert await api.default_sales_warehouse(org_unit_id) is None
