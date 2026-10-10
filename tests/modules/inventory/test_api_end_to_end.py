"""Сквозной тест складского модуля: HTTP, DI, права и настоящая база."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.seed import bootstrap_system
from myasnaya_derevnya.core.settings import settings
from myasnaya_derevnya.main import create_app
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def _root_org_unit_id(session: AsyncSession) -> UUID:
    return (
        await session.execute(
            text("select id from business.org_units where parent_id is null limit 1")
        )
    ).scalar_one()


async def _admin_session_id(session: AsyncSession) -> UUID:
    user_id = (
        await session.execute(
            text(
                "select user_id from auth.user_identities"
                " where identity_type = 'username' and identifier = :identifier"
            ),
            {"identifier": settings.initial_admin_username},
        )
    ).scalar_one()

    session_id = uuid4()
    await session.execute(
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
    await session.commit()

    return session_id


@pytest.fixture
async def client(db_session: AsyncSession):
    await bootstrap_system()
    session_id = await _admin_session_id(db_session)

    transport = ASGITransport(app=create_app())
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {session_id}"},
    ) as api_client:
        yield api_client


async def test_request_without_session_is_unauthorized(
    db_session: AsyncSession,
) -> None:
    await bootstrap_system()

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as anonymous:
        response = await anonymous.get("/api/inventory/warehouses")

    assert response.status_code == 401


async def _create_warehouse(client: AsyncClient, session: AsyncSession) -> str:
    root_org_unit_id = await _root_org_unit_id(session)

    created = await client.post(
        "/api/inventory/warehouses",
        json={
            "org_unit_id": str(root_org_unit_id),
            "code": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Сырьё",
            "type": "raw",
        },
    )
    assert created.status_code == 201, created.text

    return created.json()["warehouse_id"]


async def _create_nomenclature(client: AsyncClient) -> str:
    category = await client.post(
        "/api/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    nomenclature = await client.post(
        "/api/nomenclatures",
        json={
            "sku": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Говядина",
            "unit": "kg",
            "type": "raw_material",
            "category_id": category.json()["category_id"],
        },
    )
    assert nomenclature.status_code == 201, nomenclature.text

    return nomenclature.json()["nomenclature_id"]


async def test_full_receipt_flow_through_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    warehouse_id = await _create_warehouse(client, db_session)
    nomenclature_id = await _create_nomenclature(client)

    listed = await client.get("/api/inventory/warehouses")
    assert listed.status_code == 200
    assert warehouse_id in [item["id"] for item in listed.json()]

    # /roles объявлен раньше /{employee_id}: иначе «roles» разбирался бы как UUID.
    roles = await client.get("/api/employees/roles")
    assert roles.status_code == 200, roles.text
    assert any(item["code"] == settings.admin_role_code for item in roles.json())

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "warehouse_id": warehouse_id,
            "occurred_at": "2026-10-01T12:00:00+00:00",
            "supplier_name": "Мясокомбинат",
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "10",
                    "unit_cost": "450",
                    "lot_code": "L-001",
                }
            ],
        },
    )
    assert receipt.status_code == 201, receipt.text
    receipt_id = receipt.json()["receipt_id"]

    posted = await client.post(f"/api/inventory/receipts/{receipt_id}/post")
    assert posted.status_code == 200, posted.text

    balance = await client.get(
        f"/api/inventory/warehouses/{warehouse_id}/balances/{nomenclature_id}"
    )
    assert balance.status_code == 200, balance.text
    payload = balance.json()
    assert Decimal(payload["quantity"]) == Decimal(10)
    assert payload["total_value_kopecks"] == 450000
    assert Decimal(payload["average_unit_cost"]) == Decimal(450)

    balances = await client.get(f"/api/inventory/warehouses/{warehouse_id}/balances")
    assert balances.status_code == 200
    assert balances.json()["total"] == 1

    reposted = await client.post(f"/api/inventory/receipts/{receipt_id}/post")
    assert reposted.status_code == 409
    assert reposted.json()["error"] == "DocumentAlreadyPostedError"


async def test_write_off_uses_average_cost_through_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    warehouse_id = await _create_warehouse(client, db_session)
    nomenclature_id = await _create_nomenclature(client)

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "warehouse_id": warehouse_id,
            "occurred_at": "2026-10-01T12:00:00+00:00",
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "10",
                    "unit_cost": "500",
                    "lot_code": "L-002",
                }
            ],
        },
    )
    receipt_id = receipt.json()["receipt_id"]
    await client.post(f"/api/inventory/receipts/{receipt_id}/post")

    write_off = await client.post(
        "/api/inventory/write-offs",
        json={
            "warehouse_id": warehouse_id,
            "occurred_at": "2026-10-02T12:00:00+00:00",
            "reason": "Просрочка",
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "4",
                    "lot_code": "L-002",
                }
            ],
        },
    )
    assert write_off.status_code == 201, write_off.text
    write_off_id = write_off.json()["write_off_id"]

    posted = await client.post(f"/api/inventory/write-offs/{write_off_id}/post")
    assert posted.status_code == 200, posted.text

    balance = await client.get(
        f"/api/inventory/warehouses/{warehouse_id}/balances/{nomenclature_id}"
    )
    payload = balance.json()
    assert Decimal(payload["quantity"]) == Decimal(6)
    # 4 кг по средней 500 = 2000 рублей
    assert payload["total_value_kopecks"] == 300000
    assert Decimal(payload["average_unit_cost"]) == Decimal(500)
