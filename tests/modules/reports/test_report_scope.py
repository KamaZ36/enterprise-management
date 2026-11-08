from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.reports.application.services.report_scope import (
    ReportScope,
)
from myasnaya_derevnya.modules.reports.domain.permissions import READ_REPORTS
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    def __init__(self, location_ids: list[UUID]) -> None:
        self.location_ids = location_ids

    async def stock_locations(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id=unit_id) for unit_id in self.location_ids]


class FakeStaffAPI:
    def __init__(self, scope: AccessScope) -> None:
        self.scope = scope
        self.checked: list[str] = []

    async def scope_for(self, user_id: UUID, permission) -> AccessScope:
        self.checked.append(permission.code)
        return self.scope


def build(scope: AccessScope, location_ids: list[UUID]):
    staff_api = FakeStaffAPI(scope)
    interactor = ReportScope(
        identity_provider=FakeIdentityProvider(),  # type: ignore[arg-type]
        business_api=FakeBusinessAPI(location_ids),  # type: ignore[arg-type]
        staff_api=staff_api,  # type: ignore[arg-type]
    )

    return interactor, staff_api


async def test_company_wide_report_scope_sees_all_points() -> None:
    interactor, staff_api = build(AccessScope.company_wide(), [uuid4(), uuid4()])

    assert await interactor.visible_org_unit_ids() is None
    assert staff_api.checked == [READ_REPORTS.code]


async def test_scoped_report_scope_returns_only_covered_points() -> None:
    allowed = uuid4()
    other = uuid4()
    interactor, _ = build(AccessScope.of({allowed}), [allowed, other])

    assert await interactor.visible_org_unit_ids() == [allowed]


async def test_scoped_report_scope_rejects_other_point() -> None:
    allowed = uuid4()
    other = uuid4()
    interactor, _ = build(AccessScope.of({allowed}), [allowed, other])

    with pytest.raises(ForbiddenError):
        await interactor.visible_org_unit_ids(other)


async def test_empty_scope_is_forbidden() -> None:
    interactor, _ = build(AccessScope.of(set()), [uuid4()])

    with pytest.raises(ForbiddenError):
        await interactor.visible_org_unit_ids()
