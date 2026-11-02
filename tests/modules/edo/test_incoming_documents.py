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
            "type": "cafe",
            "code": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Кафе",
            "address": "Тестовая, 1",
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
            "name": "Газировка",
            "unit": "pcs",
            "category_id": category.json()["category_id"],
        },
    )
    assert nomenclature.status_code == 201, nomenclature.text

    return nomenclature.json()["nomenclature_id"]


async def test_receipt_links_incoming_edo_document(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id = await _create_location(client, db_session)
    nomenclature_id = await _create_nomenclature(client)

    document = await client.post(
        "/api/edo/documents",
        json={
            "org_unit_id": org_unit_id,
            "number": "УПД-100",
            "external_id": "edo-100",
            "doc_date": "2026-10-31",
            "supplier_name": "Поставщик напитков",
        },
    )
    assert document.status_code == 201, document.text
    document_id = document.json()["document_id"]

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": org_unit_id,
            "occurred_at": OCCURRED_AT,
            "edo_document_id": document_id,
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "10",
                    "unit_cost": "50",
                }
            ],
        },
    )
    assert receipt.status_code == 201, receipt.text

    detail = await client.get(
        f"/api/inventory/receipts/{receipt.json()['receipt_id']}"
    )
    assert detail.status_code == 200, detail.text
    assert detail.json()["edo_document_id"] == document_id
    assert detail.json()["edo_document_number"] == "УПД-100"


async def test_receipt_rejects_edo_document_from_other_point(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    first_point = await _create_location(client, db_session)
    second_point = await _create_location(client, db_session)
    nomenclature_id = await _create_nomenclature(client)

    document = await client.post(
        "/api/edo/documents",
        json={
            "org_unit_id": first_point,
            "number": "УПД-200",
        },
    )
    assert document.status_code == 201, document.text

    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": second_point,
            "occurred_at": OCCURRED_AT,
            "edo_document_id": document.json()["document_id"],
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": "1",
                    "unit_cost": "1",
                }
            ],
        },
    )

    assert receipt.status_code == 400, receipt.text
    assert "другой точке" in receipt.json()["message"]
