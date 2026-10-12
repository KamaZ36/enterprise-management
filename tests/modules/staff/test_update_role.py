from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.interactors.role.update import (
    UpdateRoleCommand,
    UpdateRoleInteractor,
)
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.errors import (
    RoleIsSystemError,
    RoleNotFound,
    UnknownPermissionError,
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
        self.saved: list[Role] = []

    async def get_by_id(self, role_id: UUID) -> Role | None:
        return self.role

    async def save(self, role: Role) -> None:
        self.saved.append(role)


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def make_role(
    *,
    is_system: bool = False,
    permission_codes: frozenset[str] = frozenset({"nomenclature.read"}),
) -> Role:
    return Role.create(
        code="SENIOR_SELLER",
        name="Старший продавец",
        level=50,
        description="Работает со сменой",
        is_system=is_system,
        is_assignable=True,
        is_wildcard=False,
        permission_codes=permission_codes,
        grantable_role_ids=frozenset(),
    )


def build(role: Role | None, *, allowed: bool = True):
    repository = FakeRoleRepository(role)
    transaction_manager = FakeTransactionManager()
    interactor = UpdateRoleInteractor(
        identity_provider=FakeIdentityProvider(),
        role_repository=repository,
        access_service=FakeAccessService(allowed=allowed),
        business_api=FakeBusinessAPI(),
        transaction_manager=transaction_manager,
    )

    return interactor, repository, transaction_manager


async def test_requires_manage_permission() -> None:
    role = make_role()
    interactor, repository, _ = build(role, allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor(UpdateRoleCommand(role_id=role.id, provided=frozenset()))

    assert repository.saved == []


async def test_unknown_role_raises_not_found() -> None:
    interactor, _, _ = build(None)

    with pytest.raises(RoleNotFound):
        await interactor(UpdateRoleCommand(role_id=uuid4(), provided=frozenset()))


async def test_system_role_cannot_be_changed() -> None:
    role = make_role(is_system=True)
    interactor, repository, _ = build(role)

    with pytest.raises(RoleIsSystemError):
        await interactor(
            UpdateRoleCommand(
                role_id=role.id, provided=frozenset({"name"}), name="Новое имя"
            )
        )

    assert repository.saved == []


async def test_unknown_permission_code_is_rejected() -> None:
    role = make_role()
    interactor, repository, _ = build(role)

    with pytest.raises(UnknownPermissionError) as error:
        await interactor(
            UpdateRoleCommand(
                role_id=role.id,
                provided=frozenset({"permission_codes"}),
                permission_codes=frozenset({"nomenclature.reed"}),
            )
        )

    assert error.value.code == "nomenclature.reed"
    assert repository.saved == []
    assert role.permission_codes == frozenset({"nomenclature.read"})


async def test_name_description_and_level_are_changed() -> None:
    role = make_role()
    interactor, repository, transaction_manager = build(role)

    await interactor(
        UpdateRoleCommand(
            role_id=role.id,
            provided=frozenset({"name", "description", "level"}),
            name="Старший продавец смены",
            description=None,
            level=60,
        )
    )

    assert role.name == "Старший продавец смены"
    assert role.description is None
    assert role.level == 60
    assert repository.saved == [role]
    assert transaction_manager.commits == 1


async def test_permissions_are_replaced() -> None:
    role = make_role()
    interactor, repository, _ = build(role)

    await interactor(
        UpdateRoleCommand(
            role_id=role.id,
            provided=frozenset({"permission_codes"}),
            permission_codes=frozenset({"nomenclature.read", "inventory.balance.read"}),
        )
    )

    assert role.permission_codes == frozenset(
        {"nomenclature.read", "inventory.balance.read"}
    )
    assert repository.saved == [role]


async def test_empty_permission_set_clears_rights() -> None:
    role = make_role()
    interactor, _, _ = build(role)

    await interactor(
        UpdateRoleCommand(
            role_id=role.id,
            provided=frozenset({"permission_codes"}),
            permission_codes=frozenset(),
        )
    )

    assert role.permission_codes == frozenset()
