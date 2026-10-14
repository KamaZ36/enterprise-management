from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.business.application.dto import OrgUnitListItem
from myasnaya_derevnya.modules.business.application.interactors.list_org_units import (
    ListOrgUnitsInteractor,
)
from myasnaya_derevnya.modules.business.domain.entities.org_unit import OrgUnitType
from myasnaya_derevnya.modules.business.domain.permissions import ORG_UNIT_READ
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeStaffAPI:
    def __init__(self, scope: AccessScope) -> None:
        self.scope = scope
        self.calls: list[str] = []

    async def scope_for(self, user_id: UUID, permission) -> AccessScope:
        self.calls.append(permission.code)
        return self.scope


class FakeOrgUnitReader:
    def __init__(self) -> None:
        self.calls = 0
        self.items: list[OrgUnitListItem] = []

    async def list(self) -> list[OrgUnitListItem]:
        self.calls += 1
        return self.items


def make_item(org_unit_id: UUID, code: str, parent_id: UUID | None) -> OrgUnitListItem:
    return OrgUnitListItem(
        id=org_unit_id,
        parent_id=parent_id,
        type=OrgUnitType.CAFE if parent_id else OrgUnitType.ROOT,
        code=code,
        name=code,
        is_active=True,
        address=None,
        phone_number=None,
    )


def build(
    scope: AccessScope,
) -> tuple[ListOrgUnitsInteractor, FakeOrgUnitReader, FakeStaffAPI]:
    reader = FakeOrgUnitReader()
    staff_api = FakeStaffAPI(scope)
    interactor = ListOrgUnitsInteractor(
        identity_provider=FakeIdentityProvider(),
        org_unit_reader=reader,
        staff_api=staff_api,
    )

    return interactor, reader, staff_api


async def test_without_scope_is_forbidden() -> None:
    interactor, reader, _ = build(AccessScope.of([]))

    with pytest.raises(ForbiddenError):
        await interactor()

    assert reader.calls == 0


async def test_returns_only_units_in_scope() -> None:
    root, first, second = uuid4(), uuid4(), uuid4()
    interactor, reader, staff_api = build(AccessScope.of([root, first]))
    reader.items = [
        make_item(root, "ROOT", None),
        make_item(first, "CAFE-1", root),
        make_item(second, "CAFE-2", root),
    ]

    items = await interactor()

    assert [item.code for item in items] == ["ROOT", "CAFE-1"]
    assert staff_api.calls == [ORG_UNIT_READ.code]


async def test_company_wide_returns_everything() -> None:
    root, child = uuid4(), uuid4()
    interactor, reader, _ = build(AccessScope.company_wide())
    reader.items = [
        make_item(root, "ROOT", None),
        make_item(child, "CAFE-1", root),
    ]

    items = await interactor()

    assert [item.code for item in items] == ["ROOT", "CAFE-1"]
