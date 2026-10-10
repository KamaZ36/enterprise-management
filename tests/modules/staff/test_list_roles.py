"""Юнит-тесты интерактора списка ролей."""

from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.staff.application.dto import RoleListItem
from myasnaya_derevnya.modules.staff.application.interactors.role.list_roles import (
    ListRolesInteractor,
)
from myasnaya_derevnya.modules.staff.domain.permissions import READ_ROLES


class FakeIdentityProvider:
    async def get_current_user_id(self) -> UUID:
        return uuid4()

    async def get_current_session_id(self) -> UUID:
        return uuid4()


class FakeBusinessAPI:
    def __init__(self, root_unit_id: UUID) -> None:
        self._root_unit_id = root_unit_id

    async def get_root_unit_id(self) -> UUID:
        return self._root_unit_id


class FakeAccessService:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(self, user_id: UUID, permission, org_unit_id: UUID | None) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


class FakeRoleReader:
    def __init__(self) -> None:
        self.calls = 0
        self.items: list[RoleListItem] = []

    async def list(self) -> list[RoleListItem]:
        self.calls += 1
        return self.items


def build(
    *, allowed: bool = True
) -> tuple[ListRolesInteractor, FakeRoleReader, FakeAccessService]:
    reader = FakeRoleReader()
    access_service = FakeAccessService(allowed=allowed)
    interactor = ListRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        role_reader=reader,
        access_service=access_service,
        business_api=FakeBusinessAPI(uuid4()),
    )

    return interactor, reader, access_service


async def test_requires_read_permission() -> None:
    interactor, reader, _ = build(allowed=False)

    with pytest.raises(ForbiddenError):
        await interactor()

    assert reader.calls == 0


async def test_checks_permission_at_company_level() -> None:
    root_unit_id = uuid4()
    reader = FakeRoleReader()
    access_service = FakeAccessService()
    interactor = ListRolesInteractor(
        identity_provider=FakeIdentityProvider(),
        role_reader=reader,
        access_service=access_service,
        business_api=FakeBusinessAPI(root_unit_id),
    )

    await interactor()

    assert access_service.checked == [(READ_ROLES.code, root_unit_id)]


async def test_returns_reader_items() -> None:
    interactor, reader, _ = build()
    reader.items = [
        RoleListItem(
            id=uuid4(),
            code="SUPER_ADMIN",
            name="Технический администратор",
            level=100,
            is_system=True,
            is_assignable=False,
            is_wildcard=True,
        )
    ]

    items = await interactor()

    assert [item.code for item in items] == ["SUPER_ADMIN"]
    assert items[0].is_wildcard is True
