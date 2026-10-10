from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.interactors.revoke_role import (
    RevokeRoleCommand,
    RevokeRoleInteractor,
)
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
    RoleAssignmentStatus,
)
from myasnaya_derevnya.modules.staff.domain.errors import RoleAssignmentNotFound


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id


class FakeRoleAssignmentRepository:
    def __init__(self, assignment: RoleAssignment | None) -> None:
        self._assignment = assignment
        self.saved: list[RoleAssignment] = []

    async def get_by_id(self, assignment_id: UUID) -> RoleAssignment | None:
        if self._assignment is not None and self._assignment.id == assignment_id:
            return self._assignment
        return None

    async def save(self, assignment: RoleAssignment) -> None:
        self.saved.append(assignment)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


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


def make_assignment(*, org_unit_id: UUID | None) -> RoleAssignment:
    return RoleAssignment.create(
        user_id=uuid4(),
        role_id=uuid4(),
        org_unit_id=org_unit_id,
        include_descendants=True,
        granted_by=uuid4(),
    )


def build_interactor(
    assignment: RoleAssignment | None,
    *,
    allowed: bool = True,
    root_unit_id: UUID | None = None,
) -> tuple[
    RevokeRoleInteractor,
    FakeRoleAssignmentRepository,
    FakeTransactionManager,
    FakeAccessService,
]:
    repository = FakeRoleAssignmentRepository(assignment)
    transaction_manager = FakeTransactionManager()
    access_service = FakeAccessService(allowed)
    interactor = RevokeRoleInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        role_assignment_repository=repository,
        transaction_manager=transaction_manager,
        access_service=access_service,
        business_api=FakeBusinessAPI(root_unit_id or uuid4()),
    )
    return interactor, repository, transaction_manager, access_service


async def test_revoke_marks_assignment_revoked_and_commits() -> None:
    assignment = make_assignment(org_unit_id=uuid4())
    interactor, repository, transaction_manager, _ = build_interactor(assignment)

    await interactor(RevokeRoleCommand(assignment_id=assignment.id))

    assert assignment.status is RoleAssignmentStatus.REVOKED
    assert repository.saved == [assignment]
    assert transaction_manager.committed is True


async def test_revoke_is_denied_without_permission() -> None:
    assignment = make_assignment(org_unit_id=uuid4())
    interactor, repository, transaction_manager, access_service = build_interactor(
        assignment, allowed=False
    )

    with pytest.raises(ForbiddenError):
        await interactor(RevokeRoleCommand(assignment_id=assignment.id))

    assert assignment.status is RoleAssignmentStatus.ACTIVE
    assert repository.saved == []
    assert transaction_manager.committed is False
    assert access_service.checked_org_units == [assignment.org_unit_id]


async def test_revoke_unknown_assignment_raises_not_found() -> None:
    interactor, _, _, access_service = build_interactor(None)

    with pytest.raises(RoleAssignmentNotFound):
        await interactor(RevokeRoleCommand(assignment_id=uuid4()))

    assert access_service.checked_org_units == []


async def test_company_wide_assignment_is_checked_against_root() -> None:
    root_unit_id = uuid4()
    assignment = make_assignment(org_unit_id=None)
    interactor, _, _, access_service = build_interactor(
        assignment, root_unit_id=root_unit_id
    )

    await interactor(RevokeRoleCommand(assignment_id=assignment.id))

    assert access_service.checked_org_units == [root_unit_id]
    assert assignment.status is RoleAssignmentStatus.REVOKED


async def test_scoped_assignment_is_checked_against_its_own_unit() -> None:
    org_unit_id = uuid4()
    assignment = make_assignment(org_unit_id=org_unit_id)
    interactor, _, _, access_service = build_interactor(
        assignment, root_unit_id=uuid4()
    )

    await interactor(RevokeRoleCommand(assignment_id=assignment.id))

    assert access_service.checked_org_units == [org_unit_id]
