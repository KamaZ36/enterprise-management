from datetime import date
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.staff.application.interactors.update_employee import (
    UpdateEmployeeCommand,
    UpdateEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    async def org_unit_exists(self, org_unit_id: UUID) -> bool:
        return True


class FakeAccessService:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[UUID | None] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append(org_unit_id)
        return self.allowed


class FakeEmployeeRepository:
    def __init__(self, employee: Employee | None) -> None:
        self.employee = employee
        self.saved: list[Employee] = []

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        return self.employee

    async def save(self, employee: Employee) -> None:
        self.saved.append(employee)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_employee() -> Employee:
    return Employee.create(
        user_id=uuid4(),
        org_unit_id=uuid4(),
        first_name="Иван",
        last_name="Петров",
        middle_name="Сергеевич",
        phone_number=PhoneNumber.parse("+79001112233"),
        position="Мясник",
        hired_at=date(2026, 1, 15),
    )


def build(employee: Employee | None, *, allowed: bool = True):
    repository = FakeEmployeeRepository(employee)
    transaction_manager = FakeTransactionManager()
    interactor = UpdateEmployeeInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=repository,
        access_service=FakeAccessService(allowed=allowed),
        business_api=FakeBusinessAPI(),
        transaction_manager=transaction_manager,
    )

    return interactor, repository, transaction_manager


async def test_requires_manage_permission() -> None:
    employee = make_employee()
    interactor, repository, _ = build(employee, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(
            UpdateEmployeeCommand(
                employee_id=employee.id,
                provided=frozenset({"position"}),
                position="Мясник",
            )
        )

    assert repository.saved == []


async def test_unknown_employee_raises_not_found() -> None:
    interactor, _, _ = build(None)

    with pytest.raises(EmployeeNotFound):
        await interactor(
            UpdateEmployeeCommand(employee_id=uuid4(), provided=frozenset())
        )


async def test_position_and_phone_are_changed() -> None:
    employee = make_employee()
    interactor, repository, transaction_manager = build(employee)

    await interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id,
            provided=frozenset({"position", "phone_number"}),
            position="Обвальщик",
            phone_number="+79005554433",
        )
    )

    assert employee.position == "Обвальщик"
    assert str(employee.phone_number) == "+79005554433"
    assert repository.saved == [employee]
    assert transaction_manager.commits == 1


async def test_middle_name_can_be_cleared() -> None:
    employee = make_employee()
    interactor, _, _ = build(employee)

    await interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id,
            provided=frozenset({"middle_name"}),
            middle_name=None,
        )
    )

    assert employee.middle_name is None
    assert employee.first_name == "Иван"
    assert employee.last_name == "Петров"


async def test_dismiss_and_restore() -> None:
    employee = make_employee()
    interactor, _, _ = build(employee)

    await interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=False
        )
    )
    assert employee.is_active is False
    assert employee.dismissed_at is not None

    await interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=True
        )
    )
    assert employee.is_active is True
    assert employee.dismissed_at is None


async def test_transfer_checks_both_points_and_moves() -> None:
    employee = make_employee()
    origin = employee.org_unit_id
    target = uuid4()
    access = FakeAccessService()
    interactor = UpdateEmployeeInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=FakeEmployeeRepository(employee),
        access_service=access,
        business_api=FakeBusinessAPI(),
        transaction_manager=FakeTransactionManager(),
    )

    await interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id,
            provided=frozenset({"org_unit_id"}),
            org_unit_id=target,
        )
    )

    assert employee.org_unit_id == target
    assert set(access.checked) == {origin, target}


async def test_transfer_without_permission_on_target_is_denied() -> None:
    employee = make_employee()
    origin = employee.org_unit_id
    interactor = UpdateEmployeeInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=FakeEmployeeRepository(employee),
        access_service=FakeAccessService(allowed=False),
        business_api=FakeBusinessAPI(),
        transaction_manager=FakeTransactionManager(),
    )

    with pytest.raises(ForbiddenError):
        await interactor(
            UpdateEmployeeCommand(
                employee_id=employee.id,
                provided=frozenset({"org_unit_id"}),
                org_unit_id=uuid4(),
            )
        )

    assert employee.org_unit_id == origin
