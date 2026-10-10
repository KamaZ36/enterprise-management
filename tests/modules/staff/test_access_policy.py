from uuid import UUID, uuid4

from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.domain.permissions import (
    ASSIGN_ROLES,
    MANAGE_ROLES,
    READ_EMPLOYEES,
)
from myasnaya_derevnya.modules.staff.domain.services.policy_of_access import (
    AccessPolicy,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)


def make_role(
    *,
    level: int = 10,
    is_wildcard: bool = False,
    is_assignable: bool = True,
    is_system: bool = False,
    permission_codes: frozenset[str] = frozenset(),
    grantable_role_ids: frozenset[UUID] = frozenset(),
) -> Role:
    return Role.create(
        code=f"role_{uuid4().hex[:8]}",
        name="Роль",
        level=level,
        description=None,
        is_system=is_system,
        is_assignable=is_assignable,
        is_wildcard=is_wildcard,
        permission_codes=permission_codes,
        grantable_role_ids=grantable_role_ids,
    )


def make_assignment(
    role: Role, *, org_unit_id: UUID | None, include_descendants: bool = True
) -> ResolvedAssignment:
    assignment = RoleAssignment.create(
        user_id=uuid4(),
        role_id=role.id,
        org_unit_id=org_unit_id,
        include_descendants=include_descendants,
        granted_by=uuid4(),
    )
    return ResolvedAssignment(assignment=assignment, role=role)


# --- can -------------------------------------------------------------------


def test_role_grants_only_its_own_permission_codes() -> None:
    root = uuid4()
    role = make_role(permission_codes=frozenset({MANAGE_ROLES.code}))
    assignments = [make_assignment(role, org_unit_id=root)]
    policy = AccessPolicy()

    assert policy.can(MANAGE_ROLES, root, assignments, frozenset({root})) is True
    assert policy.can(READ_EMPLOYEES, root, assignments, frozenset({root})) is False


def test_wildcard_grants_any_permission_within_scope() -> None:
    root = uuid4()
    role = make_role(is_wildcard=True)
    assignments = [make_assignment(role, org_unit_id=root)]

    assert (
        AccessPolicy().can(READ_EMPLOYEES, root, assignments, frozenset({root})) is True
    )


def test_global_assignment_covers_target_without_org_unit() -> None:
    role = make_role(permission_codes=frozenset({MANAGE_ROLES.code}))
    assignments = [make_assignment(role, org_unit_id=None)]

    assert AccessPolicy().can(MANAGE_ROLES, None, assignments, frozenset()) is True


def test_scoped_assignment_does_not_cover_target_without_org_unit() -> None:
    """Регресс: create_role проверял право на None и был недоступен скоуп-админу."""
    root = uuid4()
    role = make_role(is_wildcard=True)
    assignments = [make_assignment(role, org_unit_id=root)]

    assert AccessPolicy().can(MANAGE_ROLES, None, assignments, frozenset()) is False


def test_assignment_covers_descendant_when_flag_is_on() -> None:
    root, child = uuid4(), uuid4()
    role = make_role(permission_codes=frozenset({MANAGE_ROLES.code}))
    assignments = [make_assignment(role, org_unit_id=root, include_descendants=True)]

    assert (
        AccessPolicy().can(MANAGE_ROLES, child, assignments, frozenset({child, root}))
        is True
    )


def test_assignment_does_not_cover_descendant_when_flag_is_off() -> None:
    root, child = uuid4(), uuid4()
    role = make_role(permission_codes=frozenset({MANAGE_ROLES.code}))
    assignments = [make_assignment(role, org_unit_id=root, include_descendants=False)]

    assert (
        AccessPolicy().can(MANAGE_ROLES, child, assignments, frozenset({child, root}))
        is False
    )


def test_unrelated_scope_is_not_covered() -> None:
    root, child, other = uuid4(), uuid4(), uuid4()
    role = make_role(is_wildcard=True)
    assignments = [make_assignment(role, org_unit_id=other)]

    assert (
        AccessPolicy().can(MANAGE_ROLES, child, assignments, frozenset({child, root}))
        is False
    )


# --- can_assign ------------------------------------------------------------


def test_cannot_assign_non_assignable_role() -> None:
    root = uuid4()
    actor_role = make_role(level=100, is_wildcard=True)
    actor = [make_assignment(actor_role, org_unit_id=root)]
    target = make_role(is_assignable=False)

    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is False


def test_wildcard_actor_can_assign_assignable_role() -> None:
    root = uuid4()
    actor_role = make_role(level=100, is_wildcard=True)
    actor = [make_assignment(actor_role, org_unit_id=root)]
    target = make_role(level=100, is_assignable=True)

    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is True


def test_actor_without_assign_permission_cannot_assign() -> None:
    root = uuid4()
    actor_role = make_role(level=100, permission_codes=frozenset({MANAGE_ROLES.code}))
    actor = [make_assignment(actor_role, org_unit_id=root)]
    target = make_role(level=50, is_assignable=True)

    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is False


def test_non_wildcard_actor_needs_grant_rule() -> None:
    root = uuid4()
    target = make_role(level=50, is_assignable=True)

    without_rule = make_role(level=100, permission_codes=frozenset({ASSIGN_ROLES.code}))
    actor = [make_assignment(without_rule, org_unit_id=root)]
    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is False

    with_rule = make_role(
        level=100,
        permission_codes=frozenset({ASSIGN_ROLES.code}),
        grantable_role_ids=frozenset({target.id}),
    )
    actor = [make_assignment(with_rule, org_unit_id=root)]
    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is True


def test_actor_cannot_assign_role_of_equal_or_higher_level() -> None:
    root = uuid4()
    target = make_role(level=100, is_assignable=True)
    actor_role = make_role(
        level=100,
        permission_codes=frozenset({ASSIGN_ROLES.code}),
        grantable_role_ids=frozenset({target.id}),
    )
    actor = [make_assignment(actor_role, org_unit_id=root)]

    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is False


def test_non_wildcard_actor_cannot_assign_system_role() -> None:
    root = uuid4()
    target = make_role(level=50, is_assignable=True, is_system=True)
    actor_role = make_role(
        level=100,
        permission_codes=frozenset({ASSIGN_ROLES.code}),
        grantable_role_ids=frozenset({target.id}),
    )
    actor = [make_assignment(actor_role, org_unit_id=root)]

    assert AccessPolicy().can_assign(target, root, actor, frozenset({root})) is False


def test_cannot_assign_outside_own_scope() -> None:
    root, other = uuid4(), uuid4()
    target = make_role(level=50, is_assignable=True)
    actor_role = make_role(level=100, is_wildcard=True)
    actor = [make_assignment(actor_role, org_unit_id=root)]

    assert AccessPolicy().can_assign(target, other, actor, frozenset({other})) is False
