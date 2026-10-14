
from uuid import UUID, uuid4

from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.domain.permissions import (
    MANAGE_EMPLOYEES,
    READ_EMPLOYEES,
)
from myasnaya_derevnya.modules.staff.domain.services.policy_of_access import (
    AccessPolicy,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)


class FakeBusinessAPI:
    def __init__(self, root_unit_id: UUID, descendants: set[UUID]) -> None:
        self._root_unit_id = root_unit_id
        self._descendants = frozenset(descendants)
        self.descendant_calls: list[set[UUID]] = []

    async def get_root_unit_id(self) -> UUID:
        return self._root_unit_id

    async def org_unit_descendants_of(self, org_unit_ids) -> frozenset[UUID]:
        self.descendant_calls.append(set(org_unit_ids))
        return self._descendants


class FakeCurrentScope:
    def __init__(self, org_unit_id: UUID | None = None) -> None:
        self._org_unit_id = org_unit_id

    def org_unit_id(self) -> UUID | None:
        return self._org_unit_id


class FakeRoleAssignmentRepository:
    def __init__(self, resolved: list[ResolvedAssignment]) -> None:
        self._resolved = resolved

    async def load_active_for_user(self, user_id: UUID) -> list[ResolvedAssignment]:
        return self._resolved


def make_resolved(
    org_unit_id: UUID | None,
    *,
    include_descendants: bool,
    permission: str = READ_EMPLOYEES.code,
) -> ResolvedAssignment:
    role = Role.create(
        code=f"ROLE-{uuid4().hex[:6]}",
        name="Роль",
        level=10,
        description=None,
        is_system=False,
        is_assignable=True,
        permission_codes=frozenset({permission}),
        grantable_role_ids=frozenset(),
    )

    return ResolvedAssignment(
        assignment=RoleAssignment.create(
            user_id=uuid4(),
            role_id=role.id,
            org_unit_id=org_unit_id,
            include_descendants=include_descendants,
            granted_by=uuid4(),
        ),
        role=role,
    )


def build(
    resolved: list[ResolvedAssignment],
    root_unit_id: UUID,
    descendants: set[UUID],
    *,
    current_scope: UUID | None = None,
) -> tuple[AccessService, FakeBusinessAPI]:
    business_api = FakeBusinessAPI(root_unit_id, descendants)
    service = AccessService(
        role_repository=None,  # type: ignore[arg-type]
        role_assignment_repository=FakeRoleAssignmentRepository(resolved),
        business_api=business_api,
        access_policy=AccessPolicy(),
        current_scope=FakeCurrentScope(current_scope),  # type: ignore[arg-type]
    )

    return service, business_api


async def test_root_with_descendants_is_company_wide() -> None:
    root = uuid4()
    child = uuid4()
    service, business_api = build(
        [make_resolved(root, include_descendants=True)],
        root_unit_id=root,
        descendants={root, child},
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.is_company_wide
    assert business_api.descendant_calls == [{root}]


async def test_scoped_assignment_expands_descendants() -> None:
    root, group, child = uuid4(), uuid4(), uuid4()
    service, _ = build(
        [make_resolved(group, include_descendants=True)],
        root_unit_id=root,
        descendants={group, child},
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert not scope.is_company_wide
    assert scope.org_unit_ids == frozenset({group, child})


async def test_exact_assignment_stays_one_unit() -> None:
    root, unit = uuid4(), uuid4()
    service, business_api = build(
        [make_resolved(unit, include_descendants=False)],
        root_unit_id=root,
        descendants={root, unit},
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.org_unit_ids == frozenset({unit})
    assert business_api.descendant_calls == []


async def test_assignment_without_point_is_company_wide() -> None:
    root = uuid4()
    service, business_api = build(
        [make_resolved(None, include_descendants=True)],
        root_unit_id=root,
        descendants={root},
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.is_company_wide
    assert business_api.descendant_calls == []


async def test_other_permission_gives_empty_scope() -> None:
    root, unit = uuid4(), uuid4()
    service, _ = build(
        [
            make_resolved(
                unit,
                include_descendants=False,
                permission=MANAGE_EMPLOYEES.code,
            )
        ],
        root_unit_id=root,
        descendants={root, unit},
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.is_empty()


async def test_current_point_narrows_scope_to_it() -> None:
    root, first, second = uuid4(), uuid4(), uuid4()
    service, _ = build(
        [make_resolved(first, include_descendants=False)],
        root_unit_id=root,
        descendants={root},
        current_scope=first,
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.org_unit_ids == frozenset({first})
    assert second not in scope.org_unit_ids


async def test_current_point_outside_scope_gives_empty() -> None:
    root, unit, foreign = uuid4(), uuid4(), uuid4()
    service, _ = build(
        [make_resolved(unit, include_descendants=False)],
        root_unit_id=root,
        descendants={root},
        current_scope=foreign,
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.is_empty()


async def test_current_point_narrows_company_wide() -> None:
    root, child = uuid4(), uuid4()
    service, _ = build(
        [make_resolved(None, include_descendants=True)],
        root_unit_id=root,
        descendants={root, child},
        current_scope=child,
    )

    scope = await service.scope_for(user_id=uuid4(), permission=READ_EMPLOYEES)

    assert scope.org_unit_ids == frozenset({child})


async def test_access_map_ignores_current_point() -> None:
    root, child = uuid4(), uuid4()
    service, _ = build(
        [make_resolved(root, include_descendants=True)],
        root_unit_id=root,
        descendants={root, child},
        current_scope=child,
    )

    access = await service.access_map(user_id=uuid4())

    assert access.scope.is_company_wide
    assert access.by_unit == {}


async def test_access_map_lists_permissions_per_point() -> None:
    root, group, child = uuid4(), uuid4(), uuid4()
    service, _ = build(
        [
            make_resolved(
                group,
                include_descendants=True,
                permission=READ_EMPLOYEES.code,
            )
        ],
        root_unit_id=root,
        descendants={group, child},
    )

    access = await service.access_map(user_id=uuid4())

    assert access.scope.org_unit_ids == frozenset({group, child})
    assert access.by_unit == {
        group: frozenset({READ_EMPLOYEES.code}),
        child: frozenset({READ_EMPLOYEES.code}),
    }
    assert access.permissions == frozenset({READ_EMPLOYEES.code})


async def test_access_map_merges_roles_of_one_point() -> None:
    root, unit = uuid4(), uuid4()
    service, _ = build(
        [
            make_resolved(unit, include_descendants=False),
            make_resolved(
                unit,
                include_descendants=False,
                permission=MANAGE_EMPLOYEES.code,
            ),
        ],
        root_unit_id=root,
        descendants={root},
    )

    access = await service.access_map(user_id=uuid4())

    assert access.by_unit[unit] == frozenset(
        {READ_EMPLOYEES.code, MANAGE_EMPLOYEES.code}
    )


async def test_access_map_of_assignment_without_point_is_company_wide() -> None:
    root, unit = uuid4(), uuid4()
    service, _ = build(
        [make_resolved(None, include_descendants=True)],
        root_unit_id=root,
        descendants={root, unit},
    )

    access = await service.access_map(user_id=uuid4())

    assert access.scope.is_company_wide
    assert access.by_unit == {}
    assert access.permissions == frozenset({READ_EMPLOYEES.code})
