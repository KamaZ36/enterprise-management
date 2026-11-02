from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db

OCCURRED_AT = "2026-10-31T08:00:00+00:00"


async def _root_org_unit_id(session: AsyncSession) -> UUID:
    return (
        await session.execute(
            text("select id from business.org_units where parent_id is null limit 1")
        )
    ).scalar_one()


async def _create_location(client: AsyncClient, session: AsyncSession) -> str:
    root_org_unit_id = await _root_org_unit_id(session)
    created = await client.post(
        "/api/business/org-units",
        json={
            "parent_id": str(root_org_unit_id),
            "type": "production",
            "code": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Цех",
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
            "name": "Мясо",
            "unit": "kg",
            "category_id": category.json()["category_id"],
        },
    )
    assert nomenclature.status_code == 201, nomenclature.text

    return nomenclature.json()["nomenclature_id"]


async def test_receipt_creates_manual_veterinary_document(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id = await _create_location(client, db_session)
    nomenclature_id = await _create_nomenclature(client)
    vsd_guid = uuid4()

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": org_unit_id,
            "occurred_at": OCCURRED_AT,
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "10",
                    "unit_cost": "100",
                    "lot_code": "LOT-VSD-1",
                    "vetis_vsd_number": "ВСД-123",
                    "vetis_vsd_guid": str(vsd_guid),
                    "vetis_batch_id": "BATCH-1",
                }
            ],
        },
    )
    assert receipt.status_code == 201, receipt.text

    posted = await client.post(
        f"/api/inventory/receipts/{receipt.json()['receipt_id']}/post"
    )
    assert posted.status_code == 200, posted.text

    documents = await client.get(
        "/api/veterinary/documents",
        params={"org_unit_id": org_unit_id},
    )
    assert documents.status_code == 200, documents.text
    items = documents.json()["items"]
    assert len(items) == 1
    assert items[0]["number"] == "ВСД-123"
    assert items[0]["guid"] == str(vsd_guid)
    assert items[0]["batch_id"] == "BATCH-1"
    assert items[0]["source"] == "manual"

    lot_row = (
        await db_session.execute(
            text(
                "select veterinary_document_id "
                "from inventory.stock_lots where lot_code = 'LOT-VSD-1'"
            )
        )
    ).one()
    assert str(lot_row[0]) == items[0]["id"]

    repeated = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": org_unit_id,
            "occurred_at": OCCURRED_AT,
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "5",
                    "unit_cost": "100",
                    "lot_code": "LOT-VSD-1",
                    "vetis_vsd_number": "ВСД-123",
                    "vetis_vsd_guid": str(vsd_guid),
                    "vetis_batch_id": "BATCH-1",
                }
            ],
        },
    )
    assert repeated.status_code == 201, repeated.text
    repeated_posted = await client.post(
        f"/api/inventory/receipts/{repeated.json()['receipt_id']}/post"
    )
    assert repeated_posted.status_code == 200, repeated_posted.text

    repeated_documents = await client.get(
        "/api/veterinary/documents",
        params={"org_unit_id": org_unit_id},
    )
    assert repeated_documents.status_code == 200, repeated_documents.text
    assert len(repeated_documents.json()["items"]) == 1
