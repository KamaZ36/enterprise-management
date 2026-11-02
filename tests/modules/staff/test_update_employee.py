from dataclasses import dataclass, field
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


class FakeRoleAssignmentRepository:
    def __init__(self, revoked: int = 0) -> None:
        self.revoked = revoked
        self.revoked_for: list[UUID] = []

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        self.revoked_for.append(user_id)
        return self.revoked


class FakeAuthAPI:
    def __init__(self) -> None:
        self.changes: list[tuple[UUID, bool]] = []

    async def set_user_active(self, user_id: UUID, is_active: bool) -> None:
        self.changes.append((user_id, is_active))


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


@dataclass
class Harness:
    interactor: UpdateEmployeeInteractor
    repository: FakeEmployeeRepository
    transactions: FakeTransactionManager = field(
        default_factory=FakeTransactionManager
    )
    roles: FakeRoleAssignmentRepository = field(
        default_factory=FakeRoleAssignmentRepository
    )
    auth: FakeAuthAPI = field(default_factory=FakeAuthAPI)


def build(
    employee: Employee | None,
    *,
    allowed: bool = True,
    revoked: int = 0,
) -> Harness:
    repository = FakeEmployeeRepository(employee)
    transactions = FakeTransactionManager()
    roles = FakeRoleAssignmentRepository(revoked=revoked)
    auth = FakeAuthAPI()
    interactor = UpdateEmployeeInteractor(
        identity_provider=FakeIdentityProvider(),
        employee_repository=repository,
        access_service=FakeAccessService(allowed=allowed),
        business_api=FakeBusinessAPI(),
        role_assignment_repository=roles,
        auth_api=auth,
        transaction_manager=transactions,
    )

    return Harness(
        interactor=interactor,
        repository=repository,
        transactions=transactions,
        roles=roles,
        auth=auth,
    )


async def test_requires_manage_permission() -> None:
    employee = make_employee()
    harness = build(employee, allowed=False)

    with pytest.raises(ForbiddenError):
        await harness.interactor(
            UpdateEmployeeCommand(
                employee_id=employee.id,
                provided=frozenset({"position"}),
                position="Мясник",
            )
        )

    assert harness.repository.saved == []


async def test_unknown_employee_raises_not_found() -> None:
    harness = build(None)

    with pytest.raises(EmployeeNotFound):
        await harness.interactor(
            UpdateEmployeeCommand(employee_id=uuid4(), provided=frozenset())
        )


async def test_position_and_phone_are_changed() -> None:
    employee = make_employee()
    harness = build(employee)

    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id,
            provided=frozenset({"position", "phone_number"}),
            position="Обвальщик",
            phone_number="+79005554433",
        )
    )

    assert employee.position == "Обвальщик"
    assert str(employee.phone_number) == "+79005554433"
    assert harness.repository.saved == [employee]
    assert harness.transactions.commits == 1
    assert harness.roles.revoked_for == []
    assert harness.auth.changes == []


async def test_middle_name_can_be_cleared() -> None:
    employee = make_employee()
    harness = build(employee)

    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id,
            provided=frozenset({"middle_name"}),
            middle_name=None,
        )
    )

    assert employee.middle_name is None
    assert employee.first_name == "Иван"
    assert employee.last_name == "Петров"


async def test_dismiss_revokes_roles_and_blocks_user() -> None:
    employee = make_employee()
    harness = build(employee, revoked=2)

    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=False
        )
    )

    assert employee.is_active is False
    assert employee.dismissed_at is not None
    assert harness.roles.revoked_for == [employee.user_id]
    assert harness.auth.changes == [(employee.user_id, False)]
    assert harness.transactions.commits == 1


async def test_restore_unblocks_user_but_does_not_restore_roles() -> None:
    employee = make_employee()
    harness = build(employee)

    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=False
        )
    )
    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=True
        )
    )

    assert employee.is_active is True
    assert employee.dismissed_at is None
    assert harness.auth.changes == [
        (employee.user_id, False),
        (employee.user_id, True),
    ]
    assert harness.roles.revoked_for == [employee.user_id]


async def test_repeated_dismiss_does_not_touch_access_twice() -> None:
    employee = make_employee()
    harness = build(employee)

    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=False
        )
    )
    await harness.interactor(
        UpdateEmployeeCommand(
            employee_id=employee.id, provided=frozenset(), is_active=False
        )
    )

    assert harness.roles.revoked_for == [employee.user_id]
    assert harness.auth.changes == [(employee.user_id, False)]


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
        role_assignment_repository=FakeRoleAssignmentRepository(),
        auth_api=FakeAuthAPI(),
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
        role_assignment_repository=FakeRoleAssignmentRepository(),
        auth_api=FakeAuthAPI(),
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
