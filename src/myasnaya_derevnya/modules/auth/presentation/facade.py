from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.auth.services.access_service import AccessService


class AuthFacade:
    def __init__(self, access_service: AccessService) -> None:
        self._access_service = access_service

    async def has(
        self, user_id: UUID, permission: Permission, location_id: UUID | None = None
    ) -> bool:
        return await self._access_service.has(user_id, permission.code, location_id)

    async def require(
        self, user_id: UUID, permission: Permission, location_id: UUID | None = None
    ) -> None:
        await self._access_service.require(user_id, permission.code, location_id)
