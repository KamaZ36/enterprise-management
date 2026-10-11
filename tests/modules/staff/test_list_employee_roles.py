from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.dto import EmployeeRoleListItem
from myasnaya_derevnya.modules.staff.application.interactors.list_employee_roles import (
    ListEmployeeRolesInteractor,
    ListEmployeeRolesQuery,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignmentStatus,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES


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


class FakeAccessService:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


class FakeEmployeeRepository:
    def __init__(self, employees: list[Employee]) -> None:
        self._employees = employees

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        return next((item for item in self._employees if item.id == employee_id), None)


class FakeEmployeeRoleReader:
    def __init__(self, items: list[EmployeeRoleListItem] | None = None) -> None:
        self.items = items or []
        self.calls: list[UUID] = []

    async def list_active_for_user(self, user_id: UUID) -> list[EmployeeRoleListItem]:
        self.calls.append(user_id)
        return self.items


def make_employee() -> Employee:
    return Employee.create(
        user_id=uuid4(),
        first_name="Иван",
        last_name="Петров",
        middle_name=None,
        phone_number=None,
        position="Мясник",
        hired_at=date(2026, 1, 15),
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
    employees: list[Employee], *, allowed: bool = True
) -> tuple[ListEmployeeRolesInteractor, FakeEmployeeRoleReader, FakeAccessService]:
    reader = FakeEmployeeRoleReader()
    access_service = FakeAccessService(allowed=allowed)
    interactor = ListEmployeeRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=FakeEmployeeRepository(employees),
        employee_role_reader=reader,
        access_service=access_service,
        business_api=FakeBusinessAPI(uuid4()),
    )

    return interactor, reader, access_service


async def test_requires_read_permission() -> None:
    employee = make_employee()
    interactor, reader, _ = build([employee], allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert reader.calls == []


async def test_checks_permission_at_company_level() -> None:
    employee = make_employee()
    root_unit_id = uuid4()
    reader = FakeEmployeeRoleReader()
    access_service = FakeAccessService()
    interactor = ListEmployeeRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=FakeEmployeeRepository([employee]),
        employee_role_reader=reader,
        access_service=access_service,
        business_api=FakeBusinessAPI(root_unit_id),
    )

    await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert access_service.checked == [(READ_EMPLOYEES.code, root_unit_id)]


async def test_unknown_employee_raises_not_found() -> None:
    interactor, reader, _ = build([])

    with pytest.raises(EmployeeNotFound):
        await interactor(ListEmployeeRolesQuery(employee_id=uuid4()))

    assert reader.calls == []


async def test_reads_roles_of_the_employee_user() -> None:
    employee = make_employee()
    interactor, reader, _ = build([employee])
    reader.items = [make_item()]

    items = await interactor(ListEmployeeRolesQuery(employee_id=employee.id))

    assert reader.calls == [employee.user_id]
    assert [item.role_code for item in items] == ["SHOP_ADMIN"]
    assert items[0].status is RoleAssignmentStatus.ACTIVE
