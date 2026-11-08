from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    Nomenclature,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.errors import InvalidGtinError
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    NOMENCLATURES_TABLE,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def test_gtin_lookup_returns_only_active_nomenclature(
    db_session, make_nomenclature
) -> None:
    repository = SQLAlchemyNomenclatureRepository(db_session)
    nomenclature = await make_nomenclature()
    gtin = "4600000000017"

    await db_session.execute(
        update(NOMENCLATURES_TABLE)
        .where(NOMENCLATURES_TABLE.c.id == nomenclature.id)
        .values(gtin=gtin)
    )
    await db_session.commit()

    assert await repository.get_id_by_gtin(gtin) == nomenclature.id
    assert await repository.get_id_by_gtin(f"  {gtin}  ") == nomenclature.id
    assert await repository.get_id_by_gtin("") is None

    await db_session.execute(
        update(NOMENCLATURES_TABLE)
        .where(NOMENCLATURES_TABLE.c.id == nomenclature.id)
        .values(is_active=False)
    )
    await db_session.commit()

    assert await repository.get_id_by_gtin(gtin) is None


async def test_requires_vetis_is_persisted_and_returned(
    db_session, make_nomenclature
) -> None:
    repository = SQLAlchemyNomenclatureRepository(db_session)
    nomenclature = await make_nomenclature()
    nomenclature.change_vetis_requirement(False)

    await repository.save(nomenclature)
    await db_session.commit()

    stored = await repository.get_by_id(nomenclature.id)

    assert stored is not None
    assert stored.requires_vetis is False
    assert await repository.get_vetis_requirements({nomenclature.id}) == {
        nomenclature.id: False
    }


def test_gtin_is_normalized_and_validated() -> None:
    nomenclature = Nomenclature.create(
        sku="CHEESE",
        name="Сыр",
        unit=UnitOfMeasurement.KG,
        category_id=uuid4(),
        gtin=" 4600000000017 ",
    )

    assert nomenclature.gtin == "4600000000017"

    nomenclature.change_gtin("")
    assert nomenclature.gtin is None

    nomenclature.change_gtin("  4600000000017  ")
    assert nomenclature.gtin == "4600000000017"

    for invalid in ("123", "123456789012345", "46OO000000017"):
        with pytest.raises(InvalidGtinError):
            nomenclature.change_gtin(invalid)


async def test_create_nomenclature_with_gtin_and_generated_sku(
    client: AsyncClient,
) -> None:
    category = await client.post(
        "/api/catalog/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    gtin = f"46{uuid4().int % 10**11:011d}"
    name = f"{TEST_PREFIX}Сыр с GTIN"

    created = await client.post(
        "/api/catalog/nomenclatures",
        json={
            "name": name,
            "unit": "kg",
            "category_id": category.json()["category_id"],
            "gtin": gtin,
        },
    )
    assert created.status_code == 201, created.text
    nomenclature_id = created.json()["nomenclature_id"]

    found = await client.get(
        "/api/catalog/nomenclatures",
        params={"search": gtin},
    )
    assert found.status_code == 200, found.text
    item = next(
        item for item in found.json()["items"] if item["id"] == nomenclature_id
    )

    assert item["gtin"] == gtin
    assert item["sku"].startswith("NOM-")

    updated = await client.patch(
        f"/api/catalog/nomenclatures/{nomenclature_id}",
        json={"gtin": ""},
    )
    assert updated.status_code == 200, updated.text

    after_clear = await client.get(
        "/api/catalog/nomenclatures",
        params={"search": name},
    )
    assert after_clear.status_code == 200, after_clear.text
    cleared_item = next(
        item
        for item in after_clear.json()["items"]
        if item["id"] == nomenclature_id
    )

    assert cleared_item["gtin"] is None


async def test_duplicate_gtin_is_rejected(client: AsyncClient) -> None:
    category = await client.post(
        "/api/catalog/categories",
        json={"name": f"{TEST_PREFIX}{uuid4().hex[:8]}", "parent_id": None},
    )
    assert category.status_code == 201, category.text

    gtin = f"47{uuid4().int % 10**11:011d}"
    body = {
        "name": f"{TEST_PREFIX}Первый",
        "unit": "kg",
        "category_id": category.json()["category_id"],
        "gtin": gtin,
    }

    first = await client.post("/api/catalog/nomenclatures", json=body)
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/catalog/nomenclatures",
        json={**body, "name": f"{TEST_PREFIX}Второй"},
    )
    assert second.status_code == 409, second.text
