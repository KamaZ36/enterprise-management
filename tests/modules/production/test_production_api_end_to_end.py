
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db

OCCURRED_AT = "2026-10-14T08:00:00+00:00"


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


async def _create_nomenclature(client: AsyncClient, *, name: str) -> str:
    category = await client.post(
        "/api/catalog/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    nomenclature = await client.post(
        "/api/catalog/nomenclatures",
        json={
            "sku": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": name,
            "unit": "kg",
            "category_id": category.json()["category_id"],
        },
    )
    assert nomenclature.status_code == 201, nomenclature.text

    return nomenclature.json()["nomenclature_id"]


async def _receive(
    client: AsyncClient,
    org_unit_id: str,
    nomenclature_id: str,
    *,
    quantity: str,
    unit_cost: str,
) -> None:
    receipt = await client.post(
        "/api/inventory/receipts",
        json={
            "org_unit_id": org_unit_id,
            "occurred_at": OCCURRED_AT,
            "lines": [
                {
                    "nomenclature_id": nomenclature_id,
                    "quantity": quantity,
                    "unit_cost": unit_cost,
                    "lot_code": f"LOT-{uuid4().hex[:6]}",
                }
            ],
        },
    )
    assert receipt.status_code == 201, receipt.text

    posted = await client.post(
        f"/api/inventory/receipts/{receipt.json()['receipt_id']}/post"
    )
    assert posted.status_code == 200, posted.text


async def _balance(client: AsyncClient, org_unit_id: str, nomenclature_id: str) -> dict:
    response = await client.get(
        f"/api/inventory/locations/{org_unit_id}/balances/{nomenclature_id}"
    )
    assert response.status_code == 200, response.text

    return response.json()


async def test_production_flow_moves_stock_and_absorbs_losses(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id = await _create_location(client, db_session)
    raw_id = await _create_nomenclature(client, name="Говядина лопатка")
    main_id = await _create_nomenclature(client, name="Лопатка копчёная")
    by_product_id = await _create_nomenclature(client, name="Обрезь")


    await _receive(client, org_unit_id, raw_id, quantity="100", unit_cost="400")

    tech_card = await client.post(
        "/api/production/tech-cards",
        json={
            "code": f"{TEST_PREFIX}SMOKE-{uuid4().hex[:6]}",
            "name": "Копчение лопатки",
            "basis": "input",
            "lines": [
                {"role": "component", "nomenclature_id": raw_id, "quantity": "100"},
                {
                    "role": "output",
                    "nomenclature_id": main_id,
                    "quantity": "40",
                    "output_kind": "main",
                },
                {
                    "role": "output",
                    "nomenclature_id": by_product_id,
                    "quantity": "30",
                    "output_kind": "by_product",
                },
                {"role": "loss", "loss_kind": "shrinkage", "quantity": "30"},
            ],
        },
    )
    assert tech_card.status_code == 201, tech_card.text
    tech_card_id = tech_card.json()["id"]

    card = await client.get(f"/api/production/tech-cards/{tech_card_id}")
    assert card.status_code == 200, card.text
    assert card.json()["version"] == 1
    assert len(card.json()["lines"]) == 4

    order = await client.post(
        "/api/production/orders",
        json={
            "org_unit_id": org_unit_id,
            "tech_card_id": tech_card_id,
            "batch_count": "1",
            "occurred_at": OCCURRED_AT,
        },
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]

    posted = await client.post(f"/api/production/orders/{order_id}/post")
    assert posted.status_code == 200, posted.text


    raw_balance = await _balance(client, org_unit_id, raw_id)
    assert Decimal(raw_balance["quantity"]) == 0

    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "posted"
    assert payload["location_name"] == "Цех"

    losses = [line for line in payload["lines"] if line["role"] == "loss"]
    assert len(losses) == 1
    assert losses[0]["loss_kind"] == "shrinkage"
    assert Decimal(losses[0]["actual_quantity"]) == Decimal(30)


    outputs = {
        line["nomenclature_id"]: line
        for line in payload["lines"]
        if line["role"] == "output"
    }
    main = outputs[main_id]
    by_product = outputs[by_product_id]

    assert main["cost"] + by_product["cost"] == 4000000
    assert main["cost"] == 2285714
    assert by_product["cost"] == 1714286

    main_balance = await _balance(client, org_unit_id, main_id)
    assert Decimal(main_balance["quantity"]) == Decimal(40)
    assert main_balance["total_value_kopecks"] == main["cost"]

    by_product_balance = await _balance(client, org_unit_id, by_product_id)
    assert Decimal(by_product_balance["quantity"]) == Decimal(30)
    assert by_product_balance["total_value_kopecks"] == by_product["cost"]


    reposted = await client.post(f"/api/production/orders/{order_id}/post")
    assert reposted.status_code == 409
    assert reposted.json()["error"] == "ProductionOrderNotDraftError"

    journal = await client.get(
        "/api/production/orders", params={"org_unit_id": org_unit_id}
    )
    assert journal.status_code == 200, journal.text
    assert order_id in [item["id"] for item in journal.json()["items"]]


async def test_order_without_stock_is_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id = await _create_location(client, db_session)
    raw_id = await _create_nomenclature(client, name="Свинина")
    output_id = await _create_nomenclature(client, name="Шея копчёная")

    tech_card = await client.post(
        "/api/production/tech-cards",
        json={
            "code": f"{TEST_PREFIX}EMPTY-{uuid4().hex[:6]}",
            "name": "Копчение шеи",
            "basis": "input",
            "lines": [
                {"role": "component", "nomenclature_id": raw_id, "quantity": "10"},
                {
                    "role": "output",
                    "nomenclature_id": output_id,
                    "quantity": "8",
                    "output_kind": "main",
                },
            ],
        },
    )
    tech_card_id = tech_card.json()["id"]

    order = await client.post(
        "/api/production/orders",
        json={
            "org_unit_id": org_unit_id,
            "tech_card_id": tech_card_id,
            "batch_count": "1",
            "occurred_at": OCCURRED_AT,
        },
    )
    order_id = order.json()["id"]

    posted = await client.post(f"/api/production/orders/{order_id}/post")

    assert posted.status_code == 400
    assert posted.json()["error"] == "InsufficientStockError"


    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.json()["status"] == "draft"
