"""Юнит-тесты удаления роли: системные и выданные удалять нельзя."""

from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.interactors.role.delete import (
    DeleteRoleCommand,
    DeleteRoleInteractor,
)
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.errors import (
    RoleInUseError,
    RoleIsSystemError,
    RoleNotFound,
)


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


class FakeRoleRepository:
    def __init__(self, role: Role | None) -> None:
        self.role = role
        self.deleted: list[UUID] = []

    async def get_by_id(self, role_id: UUID) -> Role | None:
        return self.role

    async def delete(self, role_id: UUID) -> None:
        self.deleted.append(role_id)


class FakeRoleAssignmentRepository:
    def __init__(self, active: int = 0) -> None:
        self.active = active

    async def count_active_for_role(self, role_id: UUID) -> int:
        return self.active


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_role(*, is_system: bool = False) -> Role:
    return Role.create(
        code="WAREHOUSE_MANAGER",
        name="Заведующий складом",
        description=None,
        level=20,
        is_system=is_system,
        is_assignable=True,
        is_wildcard=False,
        permission_codes=frozenset({"nomenclature.read"}),
        grantable_role_ids=frozenset(),
    )


def build(
    *, role: Role | None = None, allowed: bool = True, active: int = 0
) -> tuple[DeleteRoleInteractor, FakeRoleRepository, FakeTransactionManager]:
    repository = FakeRoleRepository(role)
    transaction_manager = FakeTransactionManager()
    interactor = DeleteRoleInteractor(
        identity_provider=FakeIdentityProvider(),
        role_repository=repository,
        role_assignment_repository=FakeRoleAssignmentRepository(active=active),
        access_service=FakeAccessService(allowed=allowed),
        business_api=FakeBusinessAPI(),
        transaction_manager=transaction_manager,
    )

    return interactor, repository, transaction_manager


async def test_requires_manage_roles_permission() -> None:
    role = make_role()
    interactor, repository, _ = build(role=role, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(DeleteRoleCommand(role_id=role.id))

    assert repository.deleted == []


async def test_unknown_role_raises_not_found() -> None:
    interactor, repository, _ = build(role=None)

    with pytest.raises(RoleNotFound):
        await interactor(DeleteRoleCommand(role_id=uuid4()))

    assert repository.deleted == []


async def test_system_role_cannot_be_deleted() -> None:
    role = make_role(is_system=True)
    interactor, repository, _ = build(role=role)

    with pytest.raises(RoleIsSystemError):
        await interactor(DeleteRoleCommand(role_id=role.id))

    assert repository.deleted == []


async def test_role_in_use_cannot_be_deleted() -> None:
    role = make_role()
    interactor, repository, _ = build(role=role, active=2)

    with pytest.raises(RoleInUseError) as error:
        await interactor(DeleteRoleCommand(role_id=role.id))

    assert error.value.assignments == 2
    assert repository.deleted == []


async def test_free_role_is_deleted_and_committed() -> None:
    role = make_role()
    interactor, repository, transaction_manager = build(role=role)

    await interactor(DeleteRoleCommand(role_id=role.id))

    assert repository.deleted == [role.id]
    assert transaction_manager.commits == 1
