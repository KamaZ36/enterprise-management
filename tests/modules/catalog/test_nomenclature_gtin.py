import pytest
from sqlalchemy import update

from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    NOMENCLATURES_TABLE,
)

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
