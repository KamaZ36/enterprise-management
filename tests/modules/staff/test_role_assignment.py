from uuid import uuid4

from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
    RoleAssignmentStatus,
)


def make_assignment() -> RoleAssignment:
    return RoleAssignment.create(
        user_id=uuid4(),
        role_id=uuid4(),
        org_unit_id=uuid4(),
        include_descendants=True,
        granted_by=uuid4(),
    )


def test_new_assignment_is_active() -> None:
    assignment = make_assignment()

    assert assignment.status is RoleAssignmentStatus.ACTIVE
    assert assignment.is_active is True


def test_revoke_changes_status() -> None:
    assignment = make_assignment()

    assignment.revoke()

    assert assignment.status is RoleAssignmentStatus.REVOKED
    assert assignment.is_active is False


def test_revoke_is_idempotent() -> None:
    assignment = make_assignment()

    assignment.revoke()
    assignment.revoke()

    assert assignment.status is RoleAssignmentStatus.REVOKED
