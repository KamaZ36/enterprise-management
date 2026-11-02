from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def test_update_nomenclature_requires_vetis(
    client: AsyncClient,
) -> None:
    category = await client.post(
        "/api/catalog/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    created = await client.post(
        "/api/catalog/nomenclatures",
        json={
            "sku": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Колбаса",
            "unit": "kg",
            "category_id": category.json()["category_id"],
        },
    )
    assert created.status_code == 201, created.text
    nomenclature_id = created.json()["nomenclature_id"]

    updated = await client.patch(
        f"/api/catalog/nomenclatures/{nomenclature_id}",
        json={"requires_vetis": True},
    )
    assert updated.status_code == 200, updated.text

    listed = await client.get(
        "/api/catalog/nomenclatures",
        params={"search": f"{TEST_PREFIX}"},
    )
    assert listed.status_code == 200, listed.text
    item = next(
        item
        for item in listed.json()["items"]
        if item["id"] == nomenclature_id
    )

    assert item["requires_vetis"] is True


async def test_create_nomenclature_requires_vetis(
    client: AsyncClient,
) -> None:
    category = await client.post(
        "/api/catalog/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    created = await client.post(
        "/api/catalog/nomenclatures",
        json={
            "sku": f"{TEST_PREFIX}{uuid4().hex[:8]}",
            "name": "Мясо",
            "unit": "kg",
            "category_id": category.json()["category_id"],
            "requires_vetis": True,
        },
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        "/api/catalog/nomenclatures",
        params={"search": f"{TEST_PREFIX}"},
    )
    item = next(
        item
        for item in listed.json()["items"]
        if item["id"] == created.json()["nomenclature_id"]
    )

    assert item["requires_vetis"] is True
