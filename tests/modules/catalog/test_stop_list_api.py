from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def _root_org_unit_id(session: AsyncSession) -> UUID:
    return (
        await session.execute(
            text("select id from business.org_units where parent_id is null limit 1")
        )
    ).scalar_one()


async def _create_point(client: AsyncClient, session: AsyncSession) -> str:
    created = await client.post(
        "/api/business/org-units",
        json={
            "parent_id": str(await _root_org_unit_id(session)),
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
            "name": "Суп дня",
            "unit": "pcs",
            "category_id": category.json()["category_id"],
        },
    )
    assert nomenclature.status_code == 201, nomenclature.text

    return nomenclature.json()["nomenclature_id"]


async def _bind_price_list(
    client: AsyncClient, point_id: str, price_list_id: str
) -> None:
    bound = await client.put(
        f"/api/catalog/org-units/{point_id}/price-list",
        json={"price_list_id": price_list_id},
    )
    assert bound.status_code == 200, bound.text


async def _create_price_list(client: AsyncClient) -> str:
    created = await client.post(
        "/api/catalog/price-lists",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}"},
    )
    assert created.status_code == 201, created.text

    return created.json()["price_list_id"]


async def _setup_point(
    client: AsyncClient, session: AsyncSession
) -> tuple[str, str, str]:
    point_id = await _create_point(client, session)
    nomenclature_id = await _create_nomenclature(client)
    price_list_id = await _create_price_list(client)

    priced = await client.post(
        f"/api/catalog/price-lists/{price_list_id}/prices",
        json={"nomenclature_id": nomenclature_id, "price": "199"},
    )
    assert priced.status_code == 201, priced.text

    await _bind_price_list(client, point_id, price_list_id)

    return point_id, nomenclature_id, price_list_id


async def _assortment_ids(client: AsyncClient, point_id: str) -> set[str]:
    response = await client.get(
        f"/api/catalog/org-units/{point_id}/assortment"
    )
    assert response.status_code == 200, response.text

    return {item["nomenclature_id"] for item in response.json()["items"]}


async def test_stop_list_hides_item_only_in_its_point(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    first_point, nomenclature_id, price_list_id = await _setup_point(
        client, db_session
    )
    second_point = await _create_point(client, db_session)
    await _bind_price_list(client, second_point, price_list_id)

    assert nomenclature_id in await _assortment_ids(client, first_point)
    assert nomenclature_id in await _assortment_ids(client, second_point)

    stopped = await client.post(
        f"/api/catalog/org-units/{first_point}/stop-list",
        json={"nomenclature_id": nomenclature_id},
    )
    assert stopped.status_code == 201, stopped.text

    listed = await client.get(
        f"/api/catalog/org-units/{first_point}/stop-list"
    )
    assert listed.status_code == 200, listed.text
    assert [item["nomenclature_id"] for item in listed.json()["items"]] == [
        nomenclature_id
    ]

    assert nomenclature_id not in await _assortment_ids(client, first_point)
    assert nomenclature_id in await _assortment_ids(client, second_point)

    resumed = await client.delete(
        f"/api/catalog/org-units/{first_point}/stop-list/{nomenclature_id}"
    )
    assert resumed.status_code == 200, resumed.text
    assert nomenclature_id in await _assortment_ids(client, first_point)


async def test_stopped_item_cannot_be_ordered(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point_id, nomenclature_id, _ = await _setup_point(client, db_session)

    stopped = await client.post(
        f"/api/catalog/org-units/{point_id}/stop-list",
        json={"nomenclature_id": nomenclature_id},
    )
    assert stopped.status_code == 201, stopped.text

    order = await client.post(
        "/api/orders",
        json={
            "org_unit_id": point_id,
            "channel": "pos",
            "lines": [{"nomenclature_id": nomenclature_id, "quantity": "1"}],
        },
    )

    assert order.status_code == 400, order.text
    assert "не продаётся" in order.json()["message"]


async def test_repeated_stop_is_idempotent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point_id, nomenclature_id, _ = await _setup_point(client, db_session)

    for _ in range(2):
        response = await client.post(
            f"/api/catalog/org-units/{point_id}/stop-list",
            json={"nomenclature_id": nomenclature_id},
        )
        assert response.status_code == 201, response.text

    listed = await client.get(f"/api/catalog/org-units/{point_id}/stop-list")
    assert len(listed.json()["items"]) == 1


async def test_remove_missing_stop_list_item_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point_id, nomenclature_id, _ = await _setup_point(client, db_session)

    response = await client.delete(
        f"/api/catalog/org-units/{point_id}/stop-list/{nomenclature_id}"
    )

    assert response.status_code == 404, response.text


async def test_stop_unknown_nomenclature_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    point_id = await _create_point(client, db_session)

    response = await client.post(
        f"/api/catalog/org-units/{point_id}/stop-list",
        json={"nomenclature_id": str(uuid4())},
    )

    assert response.status_code == 404, response.text
