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


async def test_request_without_session_is_unauthorized(
    db_session: AsyncSession,
) -> None:
    await bootstrap_system()

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as anonymous:
        response = await anonymous.get("/api/inventory/locations")

    assert response.status_code == 401


async def _create_location(client: AsyncClient, session: AsyncSession) -> str:
    root_org_unit_id = await _root_org_unit_id(session)

    created = await client.post(
        "/api/business/org-units",
        json={
            "parent_id": str(root_org_unit_id),
            "type": "production",
            "code": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Сырьё",
            "address": None,
            "phone_number": None,
        },
    )
    assert created.status_code == 201, created.text

    return created.json()["org_unit_id"]


async def _create_nomenclature(client: AsyncClient) -> str:
    category = await client.post(
        "/api/catalog/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    nomenclature = await client.post(
        "/api/catalog/nomenclatures",
        json={
            "sku": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Говядина",
            "unit": "kg",
            "category_id": category.json()["category_id"],
        },
    )
    assert nomenclature.status_code == 201, nomenclature.text

    return nomenclature.json()["nomenclature_id"]


async def test_full_receipt_flow_through_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id = await _create_location(client, db_session)
    nomenclature_id = await _create_nomenclature(client)

    listed = await client.get("/api/inventory/locations")
    assert listed.status_code == 200
    assert org_unit_id in [item["id"] for item in listed.json()]

    roles = await client.get("/api/staff/employees/roles")
    assert roles.status_code == 200, roles.text
    assert any(item["code"] == settings.admin_role_code for item in roles.json())

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": org_unit_id,
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
        f"/api/inventory/locations/{org_unit_id}/balances/{nomenclature_id}"
    )
    assert balance.status_code == 200, balance.text
    payload = balance.json()
    assert Decimal(payload["quantity"]) == Decimal(10)
    assert payload["total_value_kopecks"] == 450000
    assert Decimal(payload["average_unit_cost"]) == Decimal(450)

    balances = await client.get(f"/api/inventory/locations/{org_unit_id}/balances")
    assert balances.status_code == 200
    balance_payload = balances.json()
    assert balance_payload["total"] == 1
    assert balance_payload["limit"] == 50
    assert balance_payload["offset"] == 0
    assert len(balance_payload["items"]) == 1

    balances_page = await client.get(
        f"/api/inventory/locations/{org_unit_id}/balances",
        params={"limit": 1, "offset": 1},
    )
    assert balances_page.status_code == 200
    assert balances_page.json()["total"] == 1
    assert balances_page.json()["items"] == []

    balances_found = await client.get(
        f"/api/inventory/locations/{org_unit_id}/balances",
        params={"search": "Говядина"},
    )
    assert balances_found.status_code == 200
    assert balances_found.json()["total"] == 1

    balances_missing = await client.get(
        f"/api/inventory/locations/{org_unit_id}/balances",
        params={"search": "Нетакого"},
    )
    assert balances_missing.status_code == 200
    assert balances_missing.json()["total"] == 0
    assert balances_missing.json()["items"] == []

    lots = await client.get(f"/api/inventory/locations/{org_unit_id}/lots")
    assert lots.status_code == 200, lots.text
    lot_payload = lots.json()
    assert lot_payload["total"] == 1
    assert lot_payload["limit"] == 50
    assert lot_payload["offset"] == 0
    assert lot_payload["items"][0]["lot_code"] == "L-001"

    lots_found = await client.get(
        f"/api/inventory/locations/{org_unit_id}/lots",
        params={"search": "L-001"},
    )
    assert lots_found.status_code == 200, lots_found.text
    assert lots_found.json()["total"] == 1

    lots_missing = await client.get(
        f"/api/inventory/locations/{org_unit_id}/lots",
        params={"search": "Нетакого"},
    )
    assert lots_missing.status_code == 200, lots_missing.text
    assert lots_missing.json()["total"] == 0

    movements = await client.get(
        "/api/inventory/movements", params={"org_unit_id": org_unit_id}
    )
    assert movements.status_code == 200, movements.text
    movement_payload = movements.json()
    assert movement_payload["total"] == 1
    assert movement_payload["items"][0]["movement_type"] == "receipt"
    assert Decimal(movement_payload["items"][0]["quantity"]) == Decimal(10)
    assert movement_payload["items"][0]["lot_code"] == "L-001"
    assert movement_payload["items"][0]["location_name"] == "Сырьё"
    assert movement_payload["items"][0]["nomenclature_name"] == "Говядина"
    assert movement_payload["items"][0]["total_cost_kopecks"] == 450000

    filtered_movements = await client.get(
        "/api/inventory/movements",
        params={"org_unit_id": org_unit_id, "movement_types": "write_off"},
    )
    assert filtered_movements.status_code == 200, filtered_movements.text
    assert filtered_movements.json()["total"] == 0

    journal = await client.get(
        "/api/inventory/receipts", params={"org_unit_id": org_unit_id}
    )
    assert journal.status_code == 200, journal.text
    assert journal.json()["total"] == 1
    assert journal.json()["items"][0]["id"] == receipt_id

    card = await client.get(f"/api/inventory/receipts/{receipt_id}")
    assert card.status_code == 200, card.text
    assert card.json()["supplier_name"] == "Мясокомбинат"

    transfers = await client.get(
        "/api/inventory/transfers", params={"org_unit_id": org_unit_id}
    )
    assert transfers.status_code == 200, transfers.text
    assert transfers.json()["total"] == 0

    write_offs = await client.get("/api/inventory/write-offs")
    assert write_offs.status_code == 200, write_offs.text

    reposted = await client.post(f"/api/inventory/receipts/{receipt_id}/post")
    assert reposted.status_code == 409
    assert reposted.json()["error"] == "DocumentAlreadyPostedError"


async def test_write_off_uses_average_cost_through_api(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id = await _create_location(client, db_session)
    nomenclature_id = await _create_nomenclature(client)

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": org_unit_id,
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
            "org_unit_id": org_unit_id,
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
        f"/api/inventory/locations/{org_unit_id}/balances/{nomenclature_id}"
    )
    payload = balance.json()
    assert Decimal(payload["quantity"]) == Decimal(6)
    assert payload["total_value_kopecks"] == 300000
    assert Decimal(payload["average_unit_cost"]) == Decimal(500)
