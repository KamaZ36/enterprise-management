from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class StaffAPI:
    def __init__(self, access_service: AccessService) -> None:
        self._access_service = access_service

    async def can(
        self, user_id: UUID, permission: Permission, org_unit_id: UUID | None
    ) -> bool:
        return await self._access_service.can(
            user_id=user_id, permission=permission, org_unit_id=org_unit_id
        )

    async def scopes_of(
        self, user_id: UUID, permission: Permission
    ) -> list[tuple[UUID | None, bool]]:
        return await self._access_service.scopes_of(
            user_id=user_id, permission=permission
        )

    async def can_anywhere(self, user_id: UUID, permission: Permission) -> bool:
        return bool(
            await self._access_service.scopes_of(user_id=user_id, permission=permission)
        )

    async def scope_for(self, user_id: UUID, permission: Permission) -> AccessScope:
        return await self._access_service.scope_for(
            user_id=user_id, permission=permission
        )
