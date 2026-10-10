from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.interactors.get_employee_by_id import (
    GetEmployeeByIdInteractor,
    GetEmployeeByIdQuery,
)
from myasnaya_derevnya.modules.staff.application.interactors.list_employees import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    ListEmployeesInteractor,
    ListEmployeesQuery,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.sqlalchemy import (
    SQLAlchemyEmployeeRepository,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeEmployeeRepository:
    def __init__(self, employees: list[Employee]) -> None:
        self._employees = employees
        self.list_calls: list[tuple[int, int]] = []

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        return next((item for item in self._employees if item.id == employee_id), None)

    async def list(self, *, limit: int, offset: int) -> tuple[list[Employee], int]:
        self.list_calls.append((limit, offset))
        return self._employees[offset : offset + limit], len(self._employees)


class FakeAccessService:
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.checked_org_units: list[UUID | None] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked_org_units.append(org_unit_id)
        return self.allowed


class FakeBusinessAPI:
    def __init__(self, root_unit_id: UUID) -> None:
        self._root_unit_id = root_unit_id

    async def get_root_unit_id(self) -> UUID:
        return self._root_unit_id


def make_employee(*, phone_number: str | None = None) -> Employee:
    return Employee.create(
        user_id=uuid4(),
        first_name="Иван",
        last_name="Петров",
        middle_name=None,
        phone_number=phone_number,
        position="Мясник",
        hired_at=date(2026, 1, 15),
    )


def build_get_interactor(
    employees: list[Employee], *, allowed: bool = True, root_unit_id: UUID | None = None
) -> tuple[GetEmployeeByIdInteractor, FakeEmployeeRepository, FakeAccessService]:
    repository = FakeEmployeeRepository(employees)
    access_service = FakeAccessService(allowed)
    interactor = GetEmployeeByIdInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        employee_repository=repository,
        access_service=access_service,
        business_api=FakeBusinessAPI(root_unit_id or uuid4()),
    )
    return interactor, repository, access_service


def build_list_interactor(
    employees: list[Employee], *, allowed: bool = True, root_unit_id: UUID | None = None
) -> tuple[ListEmployeesInteractor, FakeEmployeeRepository, FakeAccessService]:
    repository = FakeEmployeeRepository(employees)
    access_service = FakeAccessService(allowed)
    interactor = ListEmployeesInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        employee_repository=repository,
        access_service=access_service,
        business_api=FakeBusinessAPI(root_unit_id or uuid4()),
    )
    return interactor, repository, access_service


# --- get by id --------------------------------------------------------------


async def test_get_employee_returns_entity() -> None:
    employee = make_employee()
    interactor, _, _ = build_get_interactor([employee])

    result = await interactor(GetEmployeeByIdQuery(employee_id=employee.id))

    assert result.id == employee.id


async def test_get_employee_checks_permission_at_company_level() -> None:
    root_unit_id = uuid4()
    employee = make_employee()
    interactor, _, access_service = build_get_interactor(
        [employee], root_unit_id=root_unit_id
    )

    await interactor(GetEmployeeByIdQuery(employee_id=employee.id))

    assert access_service.checked_org_units == [root_unit_id]


async def test_get_employee_is_forbidden_without_permission() -> None:
    employee = make_employee()
    interactor, _, _ = build_get_interactor([employee], allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(GetEmployeeByIdQuery(employee_id=employee.id))


async def test_get_unknown_employee_raises_not_found() -> None:
    interactor, _, _ = build_get_interactor([])

    with pytest.raises(EmployeeNotFound):
        await interactor(GetEmployeeByIdQuery(employee_id=uuid4()))


# --- list -------------------------------------------------------------------


async def test_list_returns_page_with_total() -> None:
    employees = [make_employee() for _ in range(3)]
    interactor, repository, _ = build_list_interactor(employees)

    page = await interactor(ListEmployeesQuery(limit=2, offset=1))

    assert page.items == employees[1:3]
    assert page.total == 3
    assert page.limit == 2
    assert page.offset == 1
    assert repository.list_calls == [(2, 1)]


async def test_list_limits_are_clamped() -> None:
    interactor, repository, _ = build_list_interactor([])

    await interactor(ListEmployeesQuery(limit=1000, offset=-5))

    assert repository.list_calls == [(MAX_LIMIT, 0)]


async def test_list_defaults_are_used() -> None:
    interactor, repository, _ = build_list_interactor([])

    await interactor(ListEmployeesQuery())

    assert repository.list_calls == [(DEFAULT_LIMIT, 0)]


async def test_list_is_forbidden_without_permission() -> None:
    interactor, repository, _ = build_list_interactor([], allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ListEmployeesQuery())

    assert repository.list_calls == []


# --- маппинг строки БД ------------------------------------------------------


def _row(**overrides: object) -> dict:
    row = {
        "id": uuid4(),
        "user_id": uuid4(),
        "first_name": "Иван",
        "last_name": "Петров",
        "middle_name": None,
        "phone_number": None,
        "position": "Мясник",
        "hired_at": date(2026, 1, 15),
        "dismissed_at": None,
        "created_at": datetime.now(UTC),
    }
    row.update(overrides)
    return row


def test_row_without_phone_number_is_mapped() -> None:
    """Регресс: NULL в phone_number ронял маппинг строки в сущность."""
    repository = SQLAlchemyEmployeeRepository.__new__(SQLAlchemyEmployeeRepository)

    employee = repository._to_entity(_row(phone_number=None))

    assert employee.phone_number is None


def test_row_with_phone_number_is_mapped() -> None:
    repository = SQLAlchemyEmployeeRepository.__new__(SQLAlchemyEmployeeRepository)

    employee = repository._to_entity(_row(phone_number="+79991234567"))

    assert employee.phone_number is not None
    assert str(employee.phone_number) == "+79991234567"
