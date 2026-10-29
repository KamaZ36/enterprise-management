from uuid import uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.presentation.business_api import (
    StockLocation,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_locations import (
    ListPosLocationsInteractor,
)
from myasnaya_derevnya.modules.pos.domain.permissions import (
    POS_SOURCE_MANAGE,
    POS_SOURCE_READ,
)


class FakeIdentityProvider:
    def __init__(self, user_id) -> None:
        self._user_id = user_id

    async def get_current_user_id(self):
        return self._user_id


class FakeStaffAPI:
    def __init__(self, allowed: set[str]) -> None:
        self._allowed = allowed

    async def can_anywhere(self, *, user_id, permission) -> bool:
        return permission.code in self._allowed


class FakeBusinessAPI:
    def __init__(self, locations) -> None:
        self._locations = locations

    async def stock_locations(self):
        return self._locations


def build_interactor(*allowed: str) -> ListPosLocationsInteractor:
    return ListPosLocationsInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        staff_api=FakeStaffAPI(set(allowed)),
        business_api=FakeBusinessAPI(
            [
                StockLocation(
                    id=uuid4(), code="CAFE", name="Кафе", is_active=True
                ),
                StockLocation(
                    id=uuid4(), code="SHOP", name="Магазин", is_active=False
                ),
            ]
        ),
    )


async def test_locations_are_available_to_source_readers() -> None:
    items = await build_interactor(POS_SOURCE_READ.code)()

    assert [item.name for item in items] == ["Кафе", "Магазин"]
    assert [item.is_active for item in items] == [True, False]


async def test_locations_are_available_to_source_managers() -> None:
    items = await build_interactor(POS_SOURCE_MANAGE.code)()

    assert len(items) == 2


async def test_locations_require_a_pos_permission() -> None:
    with pytest.raises(ForbiddenError):
        await build_interactor()()
