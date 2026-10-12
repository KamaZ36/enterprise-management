from datetime import date
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.interactors.reset_employee_password import (
    ResetEmployeePasswordCommand,
    ResetEmployeePasswordInteractor,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    async def get_root_unit_id(self) -> UUID:
        return uuid4()


class FakeAccessService:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        return self.allowed


class FakeEmployeeRepository:
    def __init__(self, employee: Employee | None) -> None:
        self.employee = employee

    async def get_by_id(self, employee_id: UUID) -> Employee | None:
        return self.employee


class FakeAuthAPI:
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    async def reset_employee_password(self, user_id: UUID, password: str) -> None:
        self.calls.append((user_id, password))


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


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


def build(employee: Employee | None, *, allowed: bool = True):
    auth_api = FakeAuthAPI()
    transaction_manager = FakeTransactionManager()
    interactor = ResetEmployeePasswordInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=FakeEmployeeRepository(employee),
        access_service=FakeAccessService(allowed=allowed),
        business_api=FakeBusinessAPI(),
        auth_api=auth_api,
        transaction_manager=transaction_manager,
    )

    return interactor, auth_api, transaction_manager


async def test_requires_manage_permission() -> None:
    employee = make_employee()
    interactor, auth_api, _ = build(employee, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(ResetEmployeePasswordCommand(employee_id=employee.id))

    assert auth_api.calls == []


async def test_unknown_employee_raises_not_found() -> None:
    interactor, _, _ = build(None)

    with pytest.raises(EmployeeNotFound):
        await interactor(ResetEmployeePasswordCommand(employee_id=uuid4()))


async def test_new_password_is_issued_for_employee_user() -> None:
    employee = make_employee()
    interactor, auth_api, transaction_manager = build(employee)

    issued = await interactor(ResetEmployeePasswordCommand(employee_id=employee.id))

    assert len(auth_api.calls) == 1
    user_id, password = auth_api.calls[0]
    assert user_id == employee.user_id
    assert issued["password"] == password
    assert len(password) == 8
    assert transaction_manager.commits == 1
