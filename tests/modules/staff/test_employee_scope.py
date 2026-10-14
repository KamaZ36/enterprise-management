
from datetime import date
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.dto import EmployeeListItem
from myasnaya_derevnya.modules.staff.application.interactors.get_employee_by_id import (
    GetEmployeeByIdInteractor,
    GetEmployeeByIdQuery,
)
from myasnaya_derevnya.modules.staff.application.interactors.list_employees import (
    ListEmployeesInteractor,
    ListEmployeesQuery,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeAccessService:
    def __init__(self, scope: AccessScope) -> None:
        self.scope = scope
        self.calls: list[str] = []

    async def scope_for(self, user_id: UUID, permission) -> AccessScope:
        self.calls.append(permission.code)
        return self.scope


class FakeBusinessAPI:
    async def org_unit_titles(self, org_unit_ids) -> dict[UUID, str]:
        return {}


class FakeEmployeeReader:
    def __init__(
        self,
        items: list[EmployeeListItem] | None = None,
        by_id: dict[UUID, EmployeeListItem] | None = None,
    ) -> None:
        self.items = items or []
        self.by_id = by_id or {}
        self.list_calls: list[dict] = []
        self.get_calls: list[tuple[UUID, object]] = []

    async def list(self, *, limit, offset, search=None, org_unit_ids=None):
        self.list_calls.append(
            {
                "limit": limit,
                "offset": offset,
                "search": search,
                "org_unit_ids": org_unit_ids,
            }
        )
        return self.items, len(self.items)

    async def get_by_id(self, employee_id: UUID, org_unit_ids=None):
        self.get_calls.append((employee_id, org_unit_ids))
        return self.by_id.get(employee_id)


def make_employee() -> EmployeeListItem:
    return EmployeeListItem(
        id=uuid4(),
        user_id=uuid4(),
        org_unit_id=uuid4(),
        first_name="Иван",
        last_name="Петров",
        middle_name=None,
        phone_number=None,
        position="Мясник",
        hired_at=date(2026, 1, 15),
        dismissed_at=None,
        is_active=True,
    )


def build_list(
    scope: AccessScope,
) -> tuple[ListEmployeesInteractor, FakeEmployeeReader]:
    reader = FakeEmployeeReader(items=[make_employee()])
    interactor = ListEmployeesInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_reader=reader,
        access_service=FakeAccessService(scope),
        business_api=FakeBusinessAPI(),  # type: ignore[arg-type]
    )

    return interactor, reader


def build_get(
    scope: AccessScope, employee: EmployeeListItem
) -> tuple[GetEmployeeByIdInteractor, FakeEmployeeReader]:
    reader = FakeEmployeeReader(by_id={employee.id: employee})
    interactor = GetEmployeeByIdInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_reader=reader,
        access_service=FakeAccessService(scope),
        business_api=FakeBusinessAPI(),  # type: ignore[arg-type]
    )

    return interactor, reader


async def test_list_without_scope_is_forbidden() -> None:
    interactor, reader = build_list(AccessScope.of([]))

    with pytest.raises(ForbiddenError):
        await interactor(ListEmployeesQuery())

    assert reader.list_calls == []


async def test_list_passes_scope_units_to_reader() -> None:
    unit_id = uuid4()
    interactor, reader = build_list(AccessScope.of([unit_id]))

    page = await interactor(ListEmployeesQuery(limit=10, offset=5))

    assert reader.list_calls == [
        {
            "limit": 10,
            "offset": 5,
            "search": None,
            "org_unit_ids": frozenset({unit_id}),
        }
    ]
    assert page.total == 1


async def test_list_company_wide_has_no_filter() -> None:
    interactor, reader = build_list(AccessScope.company_wide())

    await interactor(ListEmployeesQuery())

    assert reader.list_calls[0]["org_unit_ids"] is None


async def test_card_without_scope_is_forbidden() -> None:
    employee = make_employee()
    interactor, reader = build_get(AccessScope.of([]), employee)

    with pytest.raises(ForbiddenError):
        await interactor(GetEmployeeByIdQuery(employee_id=employee.id))

    assert reader.get_calls == []


async def test_card_passes_scope_units_to_reader() -> None:
    employee = make_employee()
    unit_id = uuid4()
    interactor, reader = build_get(AccessScope.of([unit_id]), employee)

    result = await interactor(GetEmployeeByIdQuery(employee_id=employee.id))

    assert reader.get_calls == [(employee.id, frozenset({unit_id}))]
    assert result.id == employee.id


async def test_foreign_employee_is_not_found() -> None:
    employee = make_employee()
    interactor, _ = build_get(AccessScope.of([uuid4()]), employee)

    with pytest.raises(EmployeeNotFound):
        await interactor(GetEmployeeByIdQuery(employee_id=uuid4()))
