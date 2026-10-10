"""Юнит-тесты интерактора списка номенклатуры: права, фильтры, пагинация."""

from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.dto import NomenclatureListItem
from myasnaya_derevnya.modules.catalog.application.interactors.list_nomenclatures import (
    MAX_LIMIT,
    ListNomenclaturesInteractor,
    ListNomenclaturesQuery,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_NOMENCLATURE


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    def __init__(self, root_unit_id: UUID) -> None:
        self._root_unit_id = root_unit_id

    async def get_root_unit_id(self) -> UUID:
        return self._root_unit_id


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


class FakeNomenclatureReader:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.items: list[NomenclatureListItem] = []
        self.total = 0

    async def list(self, **kwargs) -> tuple[list[NomenclatureListItem], int]:
        self.calls.append(kwargs)
        return self.items, self.total


def make_item(sku: str = "SKU-1") -> NomenclatureListItem:
    return NomenclatureListItem(
        id=uuid4(),
        sku=sku,
        name="Говядина",
        type=NomenclatureType.RAW_MATERIAL,
        unit=UnitOfMeasurement.KG,
        category_id=uuid4(),
        category_name="Мясо",
    )


def build(
    *, allowed: bool = True
) -> tuple[ListNomenclaturesInteractor, FakeNomenclatureReader, FakeStaffAPI]:
    reader = FakeNomenclatureReader()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = ListNomenclaturesInteractor(
        identity_provider=FakeIdentityProvider(),
        nomenclature_reader=reader,
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_requires_read_permission() -> None:
    interactor, reader, _ = build(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListNomenclaturesQuery())

    assert reader.calls == []


async def test_checks_permission_at_company_level() -> None:
    root_unit_id = uuid4()
    reader = FakeNomenclatureReader()
    staff_api = FakeStaffAPI()
    interactor = ListNomenclaturesInteractor(
        identity_provider=FakeIdentityProvider(),
        nomenclature_reader=reader,
        business_api=FakeBusinessAPI(root_unit_id),
        staff_api=staff_api,
    )

    await interactor(ListNomenclaturesQuery())

    assert staff_api.checked == [(READ_NOMENCLATURE.code, root_unit_id)]


async def test_filters_are_passed_to_reader() -> None:
    interactor, reader, _ = build()
    category_id = uuid4()

    await interactor(
        ListNomenclaturesQuery(
            search="говядина",
            type_code=NomenclatureType.RAW_MATERIAL.value,
            category_id=category_id,
            limit=10,
            offset=5,
        )
    )

    assert reader.calls == [
        {
            "search": "говядина",
            "type_code": "raw_material",
            "category_id": category_id,
            "limit": 10,
            "offset": 5,
        }
    ]


async def test_limits_are_clamped() -> None:
    interactor, reader, _ = build()

    await interactor(ListNomenclaturesQuery(limit=1000, offset=-5))

    assert reader.calls[0]["limit"] == MAX_LIMIT
    assert reader.calls[0]["offset"] == 0


async def test_blank_search_becomes_none() -> None:
    interactor, reader, _ = build()

    await interactor(ListNomenclaturesQuery(search="   "))

    assert reader.calls[0]["search"] is None


async def test_page_carries_total_and_window() -> None:
    interactor, reader, _ = build()
    reader.total = 42
    reader.items = [make_item()]

    page = await interactor(ListNomenclaturesQuery(limit=10, offset=20))

    assert page.total == 42
    assert page.limit == 10
    assert page.offset == 20
    assert [item.sku for item in page.items] == ["SKU-1"]
