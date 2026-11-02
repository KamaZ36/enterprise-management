"""Общие фейки для тестов прикладного слоя.

Каждый фейк повторяет только тот метод интерфейса, который вызывает тест.
`FakeStaffAPI` дополнительно записывает, какое право реально проверял
интерактор, — тогда тест может утверждать конкретный код права и подмена
`READ` на `UPDATE` (или наоборот) не останется незамеченной.
"""

from collections.abc import Iterable
from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.catalog.application.dto import StopListItem
from myasnaya_derevnya.modules.catalog.domain.entities.stop_list_entry import (
    StopListEntry,
)
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


class FakeStopListReader:
    def __init__(
        self,
        stopped: Iterable[UUID] = (),
        items: list[StopListItem] | None = None,
    ) -> None:
        self.stopped = set(stopped)
        self.items = items or []
        self.calls: list[tuple[UUID, list[UUID]]] = []

    async def list_by_org_unit(self, org_unit_id: UUID) -> list[StopListItem]:
        self.calls.append((org_unit_id, []))
        return self.items

    async def stopped_nomenclature_ids(
        self, org_unit_id: UUID, nomenclature_ids: Iterable[UUID]
    ) -> set[UUID]:
        ids = list(nomenclature_ids)
        self.calls.append((org_unit_id, ids))
        return {
            nomenclature_id
            for nomenclature_id in ids
            if nomenclature_id in self.stopped
        }


class FakeStopListRepository:
    def __init__(self, *, added: bool = True, removed: bool = True) -> None:
        self.added = added
        self.removed = removed
        self.entries: list[StopListEntry] = []
        self.deleted: list[tuple[UUID, UUID]] = []

    async def add(self, entry: StopListEntry) -> bool:
        self.entries.append(entry)
        return self.added

    async def delete(self, org_unit_id: UUID, nomenclature_id: UUID) -> bool:
        self.deleted.append((org_unit_id, nomenclature_id))
        return self.removed


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
