import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.db


async def test_summary_is_available_for_admin(client: AsyncClient) -> None:
    response = await client.get("/api/reports/summary")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["revenue_kopecks"] >= 0
    assert payload["stock_value_kopecks"] >= 0
    assert "problem_receipts" in payload


async def test_sales_report_is_available_for_admin(client: AsyncClient) -> None:
    response = await client.get("/api/reports/sales")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "items" in payload
    assert payload["total_receipts"] >= 0


async def test_reports_reject_reversed_period(client: AsyncClient) -> None:
    response = await client.get(
        "/api/reports/summary",
        params={"date_from": "2026-11-05", "date_to": "2026-11-01"},
    )

    assert response.status_code == 422, response.text
