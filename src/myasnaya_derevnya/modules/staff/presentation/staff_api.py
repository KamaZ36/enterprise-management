from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
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
