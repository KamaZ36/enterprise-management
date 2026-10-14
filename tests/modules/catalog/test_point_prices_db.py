
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.application.interactors.get_point_prices import (
    GetPointPricesInteractor,
    GetPointPricesQuery,
)
from myasnaya_derevnya.modules.catalog.domain.entities.price import Price
from myasnaya_derevnya.modules.catalog.domain.entities.price_list import PriceList
from myasnaya_derevnya.modules.catalog.domain.entities.price_list_binding import (
    PriceListBinding,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.sqlalchemy import (
    SQLAlchemyPriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list.sqlalchemy import (
    SQLAlchemyPriceListRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.sqlalchemy import (
    SQLAlchemyPriceListBindingRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db


async def test_point_prices_take_only_the_bound_list(
    db_session: AsyncSession, make_nomenclature
) -> None:
    marker = uuid4().hex[:6]
    first = await make_nomenclature(
        name=f"{TEST_PREFIX}A {marker}", sku=f"{TEST_PREFIX}A-{marker}"
    )
    second = await make_nomenclature(
        name=f"{TEST_PREFIX}B {marker}", sku=f"{TEST_PREFIX}B-{marker}"
    )
    unpriced = await make_nomenclature(
        name=f"{TEST_PREFIX}C {marker}", sku=f"{TEST_PREFIX}C-{marker}"
    )

    price_lists = SQLAlchemyPriceListRepository(db_session)
    price_repository = SQLAlchemyPriceRepository(db_session)
    bindings = SQLAlchemyPriceListBindingRepository(db_session)

    bound = PriceList.create(name=f"{TEST_PREFIX}Прайс {marker}")
    other = PriceList.create(name=f"{TEST_PREFIX}Другой {marker}")
    await price_lists.add(bound)
    await price_lists.add(other)

    await price_repository.add(
        Price.create(nomenclature_id=first.id, price_list_id=bound.id, value=1000)
    )
    await price_repository.add(
        Price.create(nomenclature_id=second.id, price_list_id=bound.id, value=2500)
    )
    await price_repository.add(
        Price.create(nomenclature_id=first.id, price_list_id=other.id, value=9999)
    )

    org_unit_id = uuid4()
    await bindings.save(
        PriceListBinding.create(org_unit_id=org_unit_id, price_list_id=bound.id)
    )
    await db_session.commit()

    interactor = GetPointPricesInteractor(
        binding_repository=bindings,
        price_repository=price_repository,
    )

    prices = await interactor(
        GetPointPricesQuery(
            org_unit_id=org_unit_id,
            nomenclature_ids=[first.id, second.id, unpriced.id],
        )
    )

    assert prices == {first.id: 1000, second.id: 2500}


async def test_point_without_binding_has_no_prices(
    db_session: AsyncSession,
) -> None:
    interactor = GetPointPricesInteractor(
        binding_repository=SQLAlchemyPriceListBindingRepository(db_session),
        price_repository=SQLAlchemyPriceRepository(db_session),
    )

    prices = await interactor(
        GetPointPricesQuery(org_unit_id=uuid4(), nomenclature_ids=[uuid4()])
    )

    assert prices == {}
