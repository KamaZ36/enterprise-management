from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from myasnaya_derevnya.main import create_app
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from tests.modules.pos.helpers import (
    DOKA_ORG_ID,
    PRODUCT_GUID,
    RECEIPT_GUID,
    receive,
)

pytestmark = pytest.mark.db

AGENT_INSTALL_ID = "install-api-test"


def agent_payload() -> dict:
    return {
        "source": {"doka_org_id": DOKA_ORG_ID},
        "agent": {
            "install_id": AGENT_INSTALL_ID,
            "version": "1.0.0",
            "hostname": "PC-TEST-01",
            "clock_utc": "2026-10-27T15:05:00Z",
        },
        "file": {
            "name": "Обмен_Продаж_360900586761_27.10.2026_17.56.45.xml",
            "sha256": "a" * 64,
            "exported_at": "2026-10-27T17:56:45+03:00",
        },
        "receipts": [
            {
                "guid": RECEIPT_GUID,
                "occurred_at": "2026-10-24T08:02:26+03:00",
                "kind": "sale",
                "payment_kind": "card",
                "total_kopecks": 75000,
                "subdivision_code": "1",
                "subdivision_name": "Торговый зал",
                "cashier": "Администратор",
                "shift": "422",
                "number": "1",
                "fd_number": "18747",
                "fp_number": "1603810978",
                "fn_number": "7380440902472099",
                "warnings": [],
                "lines": [
                    {
                        "guid": "A0F13AA47AF4468F8CD2EF7CF14E3674",
                        "product_guid": PRODUCT_GUID,
                        "product_name": "Медовик",
                        "unit": "кг",
                        "quantity": "0.512",
                        "price_kopecks": 25000,
                        "amount_kopecks": 25000,
                        "discount_kopecks": 0,
                        "barcode": None,
                        "mark_code": None,
                    }
                ],
            }
        ],
    }


def agent_client(raw_key: str) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
        headers={
            "Authorization": f"Bearer {raw_key}",
            "X-Install-Id": AGENT_INSTALL_ID,
            "X-Agent-Version": "1.0.0",
        },
    )


async def test_agent_and_admin_sales_flow(
    client, db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "10", "100")

    source_response = await client.post(
        "/api/pos/sources",
        json={
            "doka_org_id": DOKA_ORG_ID,
            "name": "Кафе ЗЁРНЫШКО",
            "org_unit_id": str(warehouse.id),
        },
    )
    assert source_response.status_code == 200, source_response.text
    source = source_response.json()

    locations = await client.get("/api/pos/locations")
    assert locations.status_code == 200, locations.text
    assert str(warehouse.id) in [item["id"] for item in locations.json()]

    key_response = await client.post(
        f"/api/pos/sources/{source['id']}/agents/keys",
        json={"install_id": AGENT_INSTALL_ID, "hostname": "PC-TEST-01"},
    )
    assert key_response.status_code == 200, key_response.text
    raw_key = key_response.json()["api_key"]

    async with agent_client(raw_key) as agent:
        heartbeat = await agent.post(
            "/api/pos/heartbeat",
            json={
                "install_id": AGENT_INSTALL_ID,
                "version": "1.0.0",
                "hostname": "PC-TEST-01",
                "source": {"doka_org_id": DOKA_ORG_ID},
                "status": "ok",
                "pending_receipts": 0,
                "last_success_at": None,
                "last_error": None,
                "clock_utc": "2026-10-27T15:05:00Z",
            },
        )
        assert heartbeat.status_code == 200, heartbeat.text
        assert heartbeat.json()["server_time"]

        imported = await agent.post("/api/pos/receipts", json=agent_payload())
        assert imported.status_code == 200, imported.text
        assert [item["status"] for item in imported.json()["results"]] == [
            "pending_unmapped"
        ]

        # Чужой источник в теле запроса отвергается.
        wrong_source = agent_payload()
        wrong_source["source"]["doka_org_id"] = "964896450583"
        rejected = await agent.post("/api/pos/receipts", json=wrong_source)
        assert rejected.status_code == 403

        pending = await client.get(
            "/api/pos/receipts", params={"source_id": source["id"]}
        )
        assert pending.status_code == 200, pending.text
        page = pending.json()
        assert page["total"] == 1
        assert page["items"][0]["status"] == "needs_mapping"
        assert page["items"][0]["unmapped_count"] == 1
        receipt_id = page["items"][0]["id"]

        unmapped = await client.get(
            f"/api/pos/sources/{source['id']}/unmapped-products"
        )
        assert unmapped.status_code == 200, unmapped.text
        assert [item["product_guid"] for item in unmapped.json()] == [
            PRODUCT_GUID
        ]

        mapping = await client.put(
            f"/api/pos/sources/{source['id']}/product-map",
            json={
                "doka_product_guid": PRODUCT_GUID,
                "nomenclature_id": str(nomenclature.id),
                "unit_factor": "1",
            },
        )
        assert mapping.status_code == 200, mapping.text
        assert mapping.json()["nomenclature_name"] == nomenclature.name

        detail = await client.get(f"/api/pos/receipts/{receipt_id}")
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body["status"] == "ready"
        assert body["lines"][0]["nomenclature_id"] == str(nomenclature.id)
        assert body["lines"][0]["nomenclature_name"] == nomenclature.name

        posted = await client.post(f"/api/pos/receipts/{receipt_id}/post")
        assert posted.status_code == 200, posted.text
        assert posted.json()["status"] == "posted"

        balance = await SQLAlchemyStockBalanceRepository(db_session).get(
            warehouse.id, nomenclature.id
        )
        assert balance is not None
        assert balance.quantity == Decimal(10) - Decimal("0.512")

        # Повторная доставка — duplicate, остаток не меняется.
        duplicate = await agent.post("/api/pos/receipts", json=agent_payload())
        assert duplicate.status_code == 200, duplicate.text
        assert [item["status"] for item in duplicate.json()["results"]] == [
            "duplicate"
        ]

        balance = await SQLAlchemyStockBalanceRepository(db_session).get(
            warehouse.id, nomenclature.id
        )
        assert balance is not None
        assert balance.quantity == Decimal(10) - Decimal("0.512")

        agents = await client.get(f"/api/pos/sources/{source['id']}/agents")
        assert agents.status_code == 200, agents.text
        assert agents.json()[0]["install_id"] == AGENT_INSTALL_ID

    # Отозванный ключ больше не пускает.
    agent_id = key_response.json()["agent"]["id"]
    disabled = await client.patch(
        f"/api/pos/agents/{agent_id}/active", json={"is_active": False}
    )
    assert disabled.status_code == 200, disabled.text

    async with agent_client(raw_key) as agent:
        unauthorized = await agent.post(
            "/api/pos/heartbeat",
            json={
                "install_id": AGENT_INSTALL_ID,
                "source": {"doka_org_id": DOKA_ORG_ID},
                "status": "ok",
                "pending_receipts": 0,
            },
        )
        assert unauthorized.status_code == 401
