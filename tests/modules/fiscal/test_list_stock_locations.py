from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.presentation.business_api import (
    StockLocation,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_stock_locations import (
    ListStockLocationsInteractor,
)
from tests.modules.fiscal.fakes import (
    FakeBusinessAPI,
    FakeIdentityProvider,
    FakeStaffAPI,
)


async def test_lists_stock_locations() -> None:
    shop_id = uuid4()
    business_api = FakeBusinessAPI(
        locations={
            shop_id: StockLocation(
                id=shop_id, code="SHOP-01", name="Магазин", is_active=True
            )
        }
    )
    interactor = ListStockLocationsInteractor(
        identity_provider=FakeIdentityProvider(),
        business_api=business_api,
        staff_api=FakeStaffAPI(),
    )

    items = await interactor()

    assert len(items) == 1
    assert items[0].id == shop_id
    assert items[0].name == "Магазин"


async def test_requires_permission() -> None:
    interactor = ListStockLocationsInteractor(
        identity_provider=FakeIdentityProvider(),
        business_api=FakeBusinessAPI(),
        staff_api=FakeStaffAPI(allowed=False),
    )

    with pytest.raises(ForbiddenError):
        await interactor()
