"""Юнит-тесты интерактора списка категорий."""

from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.catalog.application.dto import CategoryListItem
from myasnaya_derevnya.modules.catalog.application.interactors.list_categories import (
    ListCategoriesInteractor,
    ListCategoriesQuery,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import READ_CATEGORY


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


class FakeCategoryReader:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.items: list[CategoryListItem] = []

    async def list(self, **kwargs) -> list[CategoryListItem]:
        self.calls.append(kwargs)
        return self.items


def build(
    *, allowed: bool = True
) -> tuple[ListCategoriesInteractor, FakeCategoryReader, FakeStaffAPI]:
    reader = FakeCategoryReader()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = ListCategoriesInteractor(
        identity_provider=FakeIdentityProvider(),
        category_reader=reader,
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_requires_read_permission() -> None:
    interactor, reader, _ = build(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListCategoriesQuery())

    assert reader.calls == []


async def test_checks_permission_at_company_level() -> None:
    root_unit_id = uuid4()
    reader = FakeCategoryReader()
    staff_api = FakeStaffAPI()
    interactor = ListCategoriesInteractor(
        identity_provider=FakeIdentityProvider(),
        category_reader=reader,
        business_api=FakeBusinessAPI(root_unit_id),
        staff_api=staff_api,
    )

    await interactor(ListCategoriesQuery())

    assert staff_api.checked == [(READ_CATEGORY.code, root_unit_id)]


async def test_search_is_passed_and_stripped() -> None:
    interactor, reader, _ = build()

    await interactor(ListCategoriesQuery(search="  мясо  "))

    assert reader.calls == [{"search": "мясо"}]


async def test_blank_search_becomes_none() -> None:
    interactor, reader, _ = build()

    await interactor(ListCategoriesQuery(search="   "))

    assert reader.calls == [{"search": None}]


async def test_returns_reader_items() -> None:
    interactor, reader, _ = build()
    parent_id = uuid4()
    reader.items = [CategoryListItem(id=uuid4(), name="Мясо", parent_id=parent_id)]

    items = await interactor(ListCategoriesQuery())

    assert [item.name for item in items] == ["Мясо"]
    assert items[0].parent_id == parent_id
