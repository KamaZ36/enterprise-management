
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.entities.price import Price
from myasnaya_derevnya.modules.catalog.domain.entities.price_list import PriceList
from myasnaya_derevnya.modules.catalog.infrastructure.readers.nomenclature_prices.price_lists import (
    SQLAlchemyPriceListsReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.sqlalchemy import (
    SQLAlchemyPriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.sqlalchemy import (
    SQLAlchemyPriceListRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def test_assortment_keeps_only_priced_positions(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    priced = await make_nomenclature(
        name=f"{TEST_PREFIX}Цена {marker}", sku=f"{TEST_PREFIX}A-{marker}"
    )
    unpriced = await make_nomenclature(
        name=f"{TEST_PREFIX}Без цены {marker}", sku=f"{TEST_PREFIX}B-{marker}"
    )

    price_list = PriceList.create(name=f"{TEST_PREFIX}Витрина {marker}")
    await SQLAlchemyPriceListRepository(db_session).add(price_list)
    await SQLAlchemyPriceRepository(db_session).add(
        Price.create(
            nomenclature_id=priced.id,
            price_list_id=price_list.id,
            value=44300,
        )
    )
    await db_session.commit()

    items = await SQLAlchemyPriceListsReader(db_session).list_assortment(price_list.id)

    assert [item.nomenclature_id for item in items] == [priced.id]
    assert items[0].value == 44300
    assert items[0].unit is UnitOfMeasurement.KG
    assert unpriced.id not in {item.nomenclature_id for item in items}
