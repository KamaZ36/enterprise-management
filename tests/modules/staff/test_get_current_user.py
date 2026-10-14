from datetime import date
from uuid import UUID, uuid4

from myasnaya_derevnya.core.permissions import all_permissions
from myasnaya_derevnya.modules.staff.application.interactors.get_current_user import (
    GetCurrentUserInteractor,
)
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessMap,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self.user_id

    async def get_current_session_id(self) -> UUID:
        return self.user_id


class FakeEmployeeRepository:
    def __init__(self, employee: Employee | None) -> None:
        self.employee = employee

    async def get_by_user_id(self, user_id: UUID) -> Employee | None:
        if self.employee is not None and self.employee.user_id == user_id:
            return self.employee

        return None


class FakeBusinessAPI:
    async def org_unit_titles(self, org_unit_ids: object) -> dict[object, str]:
        return {}


class FakeRoleAssignmentRepository:
    def __init__(self, assignments: list[ResolvedAssignment]) -> None:
        self.assignments = assignments
        self.calls: list[UUID] = []

    async def load_active_for_user(self, user_id: UUID) -> list[ResolvedAssignment]:
        self.calls.append(user_id)
        return self.assignments


class FakeAccessService:
    def __init__(self, assignments: list[ResolvedAssignment]) -> None:
        self.assignments = assignments

    async def access_map(self, user_id: UUID) -> AccessMap:
        company_wide = any(
            item.assignment.org_unit_id is None for item in self.assignments
        )
        union: set[str] = set()
        by_unit: dict[UUID, set[str]] = {}

        for item in self.assignments:
            codes = (
                frozenset(permission.code for permission in all_permissions())
                if item.role.is_wildcard
                else item.role.permission_codes
            )
            union |= codes

            unit_id = item.assignment.org_unit_id
            if unit_id is not None:
                by_unit.setdefault(unit_id, set()).update(codes)

        if company_wide:
            return AccessMap(
                scope=AccessScope.company_wide(),
                permissions=frozenset(union),
                by_unit={},
            )

        return AccessMap(
            scope=AccessScope.of(by_unit),
            permissions=frozenset(union),
            by_unit={unit_id: frozenset(codes) for unit_id, codes in by_unit.items()},
        )


def make_role(*, wildcard: bool, codes: frozenset[str] = frozenset()) -> Role:
    return Role.create(
        code="SHOP_ADMIN",
        name="Администратор магазина",
        description=None,
        level=50,
        is_system=False,
        is_assignable=True,
        is_wildcard=wildcard,
        permission_codes=codes,
        grantable_role_ids=frozenset(),
    )


def make_assignment(
    user_id: UUID, role: Role, org_unit_id: UUID | None
) -> ResolvedAssignment:
    return ResolvedAssignment(
        assignment=RoleAssignment.create(
            user_id=user_id,
            role_id=role.id,
            org_unit_id=org_unit_id,
            include_descendants=True,
            granted_by=uuid4(),
        ),
        role=role,
    )


def make_employee(user_id: UUID) -> Employee:
    return Employee.create(
        user_id=user_id,
        org_unit_id=uuid4(),
        first_name="Иван",
        last_name="Петров",
        middle_name=None,
        phone_number=None,
        position="Мясник",
        hired_at=date(2026, 1, 15),
    )


def build(
    user_id: UUID,
    assignments: list[ResolvedAssignment],
    employee: Employee | None = None,
) -> tuple[GetCurrentUserInteractor, FakeRoleAssignmentRepository]:
    repository = FakeRoleAssignmentRepository(assignments)

    return (
        GetCurrentUserInteractor(
            identity_provider=FakeIdentityProvider(user_id),
            employee_repository=FakeEmployeeRepository(employee),
            role_assignment_repository=repository,
            access_service=FakeAccessService(assignments),  # type: ignore[arg-type]
            business_api=FakeBusinessAPI(),
        ),
        repository,
    )


async def test_wildcard_role_grants_every_permission() -> None:
    user_id = uuid4()
    interactor, _ = build(
        user_id, [make_assignment(user_id, make_role(wildcard=True), None)]
    )

    view = await interactor()

    assert view.permissions == frozenset(
        permission.code for permission in all_permissions()
    )
    assert len(view.permissions) == len(all_permissions())


async def test_scoped_role_grants_own_permissions_only() -> None:
    user_id = uuid4()
    role = make_role(wildcard=False, codes=frozenset({"nomenclature.read"}))
    interactor, _ = build(user_id, [make_assignment(user_id, role, uuid4())])

    view = await interactor()

    assert view.permissions == frozenset({"nomenclature.read"})


async def test_permissions_of_several_roles_are_merged() -> None:
    user_id = uuid4()
    first = make_role(wildcard=False, codes=frozenset({"nomenclature.read"}))
    second = make_role(wildcard=False, codes=frozenset({"inventory.balance.read"}))

    interactor, _ = build(
        user_id,
        [
            make_assignment(user_id, first, uuid4()),
            make_assignment(user_id, second, uuid4()),
        ],
    )

    view = await interactor()

    assert view.permissions == frozenset(
        {"nomenclature.read", "inventory.balance.read"}
    )


async def test_user_without_assignments_sees_nothing() -> None:
    user_id = uuid4()
    interactor, repository = build(user_id, [])

    view = await interactor()

    assert view.permissions == frozenset()
    assert view.roles == []
    assert view.employee_id is None
    assert (view.first_name, view.last_name, view.position) == (None, None, None)
    assert repository.calls == [user_id]


async def test_employee_is_attached_to_the_view() -> None:
    user_id = uuid4()
    employee = make_employee(user_id)
    role = make_role(wildcard=False, codes=frozenset({"nomenclature.read"}))
    org_unit_id = uuid4()

    interactor, _ = build(
        user_id, [make_assignment(user_id, role, org_unit_id)], employee
    )

    view = await interactor()

    assert view.employee_id == employee.id
    assert view.last_name == "Петров"
    assert view.position == "Мясник"
    assert [(item.code, item.org_unit_id) for item in view.roles] == [
        ("SHOP_ADMIN", org_unit_id)
    ]


async def test_assigned_points_become_scope_options() -> None:
    user_id = uuid4()
    org_unit_id = uuid4()
    role = make_role(wildcard=False, codes=frozenset({"nomenclature.read"}))
    interactor, _ = build(user_id, [make_assignment(user_id, role, org_unit_id)])

    view = await interactor()

    assert [item.id for item in view.scopes] == [org_unit_id]
    assert view.scopes[0].permissions == frozenset({"nomenclature.read"})


async def test_scope_permissions_are_reported_per_point() -> None:
    user_id = uuid4()
    first_unit, second_unit = uuid4(), uuid4()
    first_role = make_role(wildcard=False, codes=frozenset({"order.read"}))
    second_role = make_role(wildcard=False, codes=frozenset({"inventory.balance.read"}))

    interactor, _ = build(
        user_id,
        [
            make_assignment(user_id, first_role, first_unit),
            make_assignment(user_id, second_role, second_unit),
        ],
    )

    view = await interactor()

    by_unit = {item.id: item.permissions for item in view.scopes}
    assert by_unit[first_unit] == frozenset({"order.read"})
    assert by_unit[second_unit] == frozenset({"inventory.balance.read"})
    assert view.permissions == frozenset({"order.read", "inventory.balance.read"})


async def test_company_wide_has_no_scope_options() -> None:
    user_id = uuid4()
    role = make_role(wildcard=True)
    interactor, _ = build(user_id, [make_assignment(user_id, role, None)])

    view = await interactor()

    assert view.scopes == ()
    assert view.permissions == frozenset(
        permission.code for permission in all_permissions()
    )
