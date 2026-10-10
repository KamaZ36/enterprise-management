"""Юнит-тесты интерактора списка орг-единиц."""

from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem
from myasnaya_derevnya.modules.business.application.interactors.list_org_units import (
    ListOrgUnitsInteractor,
)
from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType
from myasnaya_derevnya.modules.business.domain.permissions import ORG_UNIT_READ


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


class FakeOrgUnitRepository:
    def __init__(self, root_id: UUID | None) -> None:
        self._root_id = root_id

    async def get_root_id(self) -> UUID | None:
        return self._root_id


class FakeOrgUnitReader:
    def __init__(self) -> None:
        self.calls = 0
        self.items: list[OrgUnitListItem] = []

    async def list(self) -> list[OrgUnitListItem]:
        self.calls += 1
        return self.items


def build(
    *, allowed: bool = True, root_id: UUID | None = None
) -> tuple[ListOrgUnitsInteractor, FakeOrgUnitReader, FakeStaffAPI]:
    reader = FakeOrgUnitReader()
    staff_api = FakeStaffAPI(allowed=allowed)
    interactor = ListOrgUnitsInteractor(
        identity_provider=FakeIdentityProvider(),
        org_unit_reader=reader,
        org_unit_repository=FakeOrgUnitRepository(
            root_id if root_id is not None else uuid4()
        ),
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_requires_read_permission() -> None:
    interactor, reader, _ = build(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor()

    assert reader.calls == 0


async def test_checks_permission_at_root() -> None:
    root_id = uuid4()
    interactor, _, staff_api = build(root_id=root_id)

    await interactor()

    assert staff_api.checked == [(ORG_UNIT_READ.code, root_id)]


async def test_empty_structure_returns_empty_list() -> None:
    """Если дерева ещё нет, показывать нечего и проверять нечего."""
    reader = FakeOrgUnitReader()
    staff_api = FakeStaffAPI()
    interactor = ListOrgUnitsInteractor(
        identity_provider=FakeIdentityProvider(),
        org_unit_reader=reader,
        org_unit_repository=FakeOrgUnitRepository(None),
        staff_api=staff_api,
    )

    assert await interactor() == []
    assert staff_api.checked == []
    assert reader.calls == 0


async def test_returns_reader_items() -> None:
    root_id = uuid4()
    interactor, reader, _ = build(root_id=root_id)
    reader.items = [
        OrgUnitListItem(
            id=root_id,
            parent_id=None,
            type=OrgUnitType.ROOT,
            code="ROOT",
            name="Компания",
            is_active=True,
        )
    ]

    items = await interactor()

    assert [item.code for item in items] == ["ROOT"]
    assert items[0].parent_id is None
