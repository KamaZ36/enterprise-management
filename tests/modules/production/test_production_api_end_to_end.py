
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

    empty_output = await client.post(f"/api/production/orders/{order_id}/post")
    assert empty_output.status_code == 400
    assert empty_output.json()["error"] == "EmptyProductionOutputError"

    await _fill_outputs(client, order_id)

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
    await _fill_outputs(client, order_id)

    posted = await client.post(f"/api/production/orders/{order_id}/post")

    assert posted.status_code == 400
    assert posted.json()["error"] == "InsufficientStockError"


    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.json()["status"] == "draft"


async def _fill_outputs(client: AsyncClient, order_id: str) -> None:
    """Вводит фактический выход по норме: без него задание не проводится."""

    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.status_code == 200, detail.text
    outputs = [
        line for line in detail.json()["lines"] if line["role"] == "output"
    ]

    response = await client.patch(
        f"/api/production/orders/{order_id}",
        json={
            "actuals": [
                {
                    "line_id": line["id"],
                    "quantity": line["planned_quantity"],
                }
                for line in outputs
            ]
        },
    )
    assert response.status_code == 200, response.text


async def _posted_order(
    client: AsyncClient, session: AsyncSession
) -> tuple[str, str, str, str]:
    """Создаёт проведённое задание: 100 кг сырья → 40 кг готовой продукции."""

    org_unit_id = await _create_location(client, session)
    raw_id = await _create_nomenclature(client, name="Говядина лопатка")
    output_id = await _create_nomenclature(client, name="Лопатка копчёная")

    await _receive(client, org_unit_id, raw_id, quantity="100", unit_cost="400")

    tech_card = await client.post(
        "/api/production/tech-cards",
        json={
            "code": f"{TEST_PREFIX}UNPOST-{uuid4().hex[:6]}",
            "name": "Копчение для сторно",
            "basis": "input",
            "lines": [
                {"role": "component", "nomenclature_id": raw_id, "quantity": "100"},
                {
                    "role": "output",
                    "nomenclature_id": output_id,
                    "quantity": "40",
                    "output_kind": "main",
                },
            ],
        },
    )
    assert tech_card.status_code == 201, tech_card.text

    order = await client.post(
        "/api/production/orders",
        json={
            "org_unit_id": org_unit_id,
            "tech_card_id": tech_card.json()["id"],
            "batch_count": "1",
            "occurred_at": OCCURRED_AT,
        },
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    await _fill_outputs(client, order_id)

    posted = await client.post(f"/api/production/orders/{order_id}/post")
    assert posted.status_code == 200, posted.text

    return org_unit_id, raw_id, output_id, order_id


async def _movement_count(
    client: AsyncClient, org_unit_id: str, nomenclature_id: str
) -> int:
    response = await client.get(
        "/api/inventory/movements",
        params={"org_unit_id": org_unit_id, "nomenclature_id": nomenclature_id},
    )
    assert response.status_code == 200, response.text

    return response.json()["total"]


async def test_unpost_restores_stock_and_returns_order_to_draft(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id, raw_id, output_id, order_id = await _posted_order(
        client, db_session
    )

    unposted = await client.post(f"/api/production/orders/{order_id}/unpost")
    assert unposted.status_code == 200, unposted.text

    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["status"] == "draft"
    assert payload["posted_at"] is None
    outputs = [line for line in payload["lines"] if line["role"] == "output"]
    assert outputs[0]["cost"] is None
    assert outputs[0]["lot_id"] is None

    raw_balance = await _balance(client, org_unit_id, raw_id)
    assert Decimal(raw_balance["quantity"]) == Decimal(100)
    assert raw_balance["total_value_kopecks"] == 4000000

    output_balance = await _balance(client, org_unit_id, output_id)
    assert Decimal(output_balance["quantity"]) == 0

    assert await _movement_count(client, org_unit_id, output_id) == 0
    assert await _movement_count(client, org_unit_id, raw_id) == 1

    reposted = await client.post(f"/api/production/orders/{order_id}/post")
    assert reposted.status_code == 200, reposted.text

    raw_balance = await _balance(client, org_unit_id, raw_id)
    assert Decimal(raw_balance["quantity"]) == 0
    output_balance = await _balance(client, org_unit_id, output_id)
    assert Decimal(output_balance["quantity"]) == Decimal(40)
    assert await _movement_count(client, org_unit_id, output_id) == 1


async def test_unpost_after_output_shipment_is_rejected(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    org_unit_id, _, output_id, order_id = await _posted_order(client, db_session)

    shipment = await client.post(
        "/api/inventory/shipments",
        json={
            "org_unit_id": org_unit_id,
            "occurred_at": OCCURRED_AT,
            "recipient": "Магазин на углу",
            "lines": [{"nomenclature_id": output_id, "quantity": "10"}],
        },
    )
    assert shipment.status_code == 201, shipment.text
    shipment_id = shipment.json()["shipment_id"]

    shipped = await client.post(f"/api/inventory/shipments/{shipment_id}/post")
    assert shipped.status_code == 200, shipped.text

    unposted = await client.post(f"/api/production/orders/{order_id}/unpost")
    assert unposted.status_code == 409, unposted.text
    assert unposted.json()["error"] == "DocumentCannotBeUnpostedError"

    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.json()["status"] == "posted"

    output_balance = await _balance(client, org_unit_id, output_id)
    assert Decimal(output_balance["quantity"]) == Decimal(30)


async def test_manual_order_without_tech_card(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Задание без техкарты: вход вводится при создании, выход — при проведении."""

    org_unit_id = await _create_location(client, db_session)
    raw_id = await _create_nomenclature(client, name="Фарш")
    main_id = await _create_nomenclature(client, name="Колбаса")

    await _receive(client, org_unit_id, raw_id, quantity="20", unit_cost="100")

    created = await client.post(
        "/api/production/orders",
        json={
            "org_unit_id": org_unit_id,
            "occurred_at": OCCURRED_AT,
            "components": [{"nomenclature_id": raw_id, "quantity": "20"}],
            "outputs": [{"nomenclature_id": main_id}],
        },
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]

    detail = await client.get(f"/api/production/orders/{order_id}")
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["tech_card_id"] is None
    assert payload["tech_card_code"] is None

    components = [
        line for line in payload["lines"] if line["role"] == "component"
    ]
    assert len(components) == 1
    assert Decimal(components[0]["actual_quantity"]) == Decimal(20)

    output_line = next(
        line for line in payload["lines"] if line["role"] == "output"
    )

    # Без фактического выхода провести нельзя.
    empty_output = await client.post(f"/api/production/orders/{order_id}/post")
    assert empty_output.status_code == 400
    assert empty_output.json()["error"] == "EmptyProductionOutputError"

    updated = await client.patch(
        f"/api/production/orders/{order_id}",
        json={"actuals": [{"line_id": output_line["id"], "quantity": "18"}]},
    )
    assert updated.status_code == 200, updated.text

    posted = await client.post(f"/api/production/orders/{order_id}/post")
    assert posted.status_code == 200, posted.text

    raw_balance = await _balance(client, org_unit_id, raw_id)
    assert Decimal(raw_balance["quantity"]) == 0

    main_balance = await _balance(client, org_unit_id, main_id)
    assert Decimal(main_balance["quantity"]) == Decimal(18)

    posted_payload = (
        await client.get(f"/api/production/orders/{order_id}")
    ).json()

    losses = [line for line in posted_payload["lines"] if line["role"] == "loss"]
    assert len(losses) == 1
    assert Decimal(losses[0]["actual_quantity"]) == Decimal(2)

    # 20 кг по 100 ₽ = 2000 ₽ ушло на 18 кг выхода.
    output = next(line for line in posted_payload["lines"] if line["role"] == "output")
    assert output["cost"] == 200000
    assert main_balance["total_value_kopecks"] == 200000

    # Отчёт по производству не падает на задании без техкарты и группирует
    # такие задания по выпускаемой позиции.
    report = await client.get(
        "/api/reports/production",
        params={"date_from": "2026-10-14", "date_to": "2026-10-14"},
    )
    assert report.status_code == 200, report.text

    manual_rows = [
        row for row in report.json()["items"] if row["tech_card_code"] is None
    ]
    assert manual_rows
    assert any(row["product_name"] == "Колбаса" for row in manual_rows)
