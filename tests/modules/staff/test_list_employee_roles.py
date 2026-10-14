from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.dto import (
    EmployeeListItem,
    EmployeeRoleListItem,
)
from myasnaya_derevnya.modules.staff.application.interactors.list_employee_roles import (
    ListEmployeeRolesInteractor,
    ListEmployeeRolesQuery,
)
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignmentStatus,
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


class FakeEmployeeReader:
    def __init__(self, employee: EmployeeListItem | None = None) -> None:
        self.employee = employee
        self.get_calls: list[tuple[UUID, object]] = []

    async def get_by_id(self, employee_id: UUID, org_unit_ids=None):
        self.get_calls.append((employee_id, org_unit_ids))

        if self.employee is not None and self.employee.id == employee_id:
            return self.employee

        return None


class FakeEmployeeRoleReader:
    def __init__(self, items: list[EmployeeRoleListItem] | None = None) -> None:
        self.items = items or []
        self.calls: list[UUID] = []

    async def list_active_for_user(self, user_id: UUID) -> list[EmployeeRoleListItem]:
        self.calls.append(user_id)
        return self.items


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


def make_item() -> EmployeeRoleListItem:
    return EmployeeRoleListItem(
        id=uuid4(),
        role_id=uuid4(),
        role_code="SHOP_ADMIN",
        role_name="Администратор магазина",
        org_unit_id=uuid4(),
        include_descendants=True,
        status=RoleAssignmentStatus.ACTIVE,
        assigned_at=datetime(2026, 10, 11, 12, 0, tzinfo=UTC),
    )


def build(
    *,
    scope: AccessScope,
    employee: EmployeeListItem | None = None,
) -> tuple[
    ListEmployeeRolesInteractor, FakeEmployeeReader, FakeEmployeeRoleReader, UUID
]:
    reader = FakeEmployeeReader(employee)
    role_reader = FakeEmployeeRoleReader()
    access_service = FakeAccessService(scope)
    interactor = ListEmployeeRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_reader=reader,
        employee_role_reader=role_reader,
        access_service=access_service,
    )

    unit_id = next(iter(scope.org_unit_ids), uuid4())

    return interactor, reader, role_reader, unit_id


async def test_without_scope_is_forbidden() -> None:
    employee = make_employee()
    interactor, reader, role_reader, _ = build(
        scope=AccessScope.of([]), employee=employee
    )

    with pytest.raises(ForbiddenError):
        await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert reader.get_calls == []
    assert role_reader.calls == []


async def test_passes_scope_filter_to_reader() -> None:
    employee = make_employee()
    unit_id = uuid4()
    reader = FakeEmployeeReader(employee)
    role_reader = FakeEmployeeRoleReader()
    interactor = ListEmployeeRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_reader=reader,
        employee_role_reader=role_reader,
        access_service=FakeAccessService(AccessScope.of([unit_id])),
    )

    await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert reader.get_calls == [(employee.id, frozenset({unit_id}))]


async def test_company_wide_scope_has_no_filter() -> None:
    employee = make_employee()
    reader = FakeEmployeeReader(employee)
    interactor = ListEmployeeRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_reader=reader,
        employee_role_reader=FakeEmployeeRoleReader(),
        access_service=FakeAccessService(AccessScope.company_wide()),
    )

    await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert reader.get_calls == [(employee.id, None)]


async def test_foreign_employee_is_not_found() -> None:
    interactor, _reader, role_reader, _ = build(scope=AccessScope.of([uuid4()]))

    with pytest.raises(EmployeeNotFound):
        await interactor(ListEmployeeRolesQuery(employee_id=uuid4()))

    assert role_reader.calls == []


async def test_reads_roles_of_the_employee_user() -> None:
    employee = make_employee()
    interactor, _, role_reader, _ = build(
        scope=AccessScope.of([uuid4()]), employee=employee
    )
    role_reader.items = [make_item()]

    items = await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert role_reader.calls == [employee.user_id]
    assert [item.role_code for item in items] == ["SHOP_ADMIN"]
    assert items[0].status is RoleAssignmentStatus.ACTIVE
