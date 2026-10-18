"""Общие фейки для тестов прикладного слоя.

Каждый фейк повторяет только тот метод интерфейса, который вызывает тест.
`FakeStaffAPI` дополнительно записывает, какое право реально проверял
интерактор, — тогда тест может утверждать конкретный код права и подмена
`READ` на `UPDATE` (или наоборот) не останется незамеченной.
"""

from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id

    async def get_current_session_id(self) -> UUID:
        return self._user_id


class FakeTransactionManager:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakeStaffAPI:
    def __init__(
        self,
        *,
        allowed: bool = True,
        scope: AccessScope | None = None,
    ) -> None:
        self.allowed = allowed
        self.scope = scope if scope is not None else AccessScope.company_wide()
        self.checked: list[tuple[str, UUID | None]] = []
        self.scope_checked: list[str] = []

    async def can(
        self, user_id: UUID, permission: Permission, org_unit_id: UUID | None
    ) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed

    async def can_anywhere(
        self, *, user_id: UUID, permission: Permission
    ) -> bool:
        self.checked.append((permission.code, None))
        return self.allowed

    async def scope_for(
        self, user_id: UUID, permission: Permission
    ) -> AccessScope:
        self.scope_checked.append(permission.code)
        return self.scope
