from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.modules.auth.infrastructure.readers.access_reader.base import (
    AccessReader,
)


class AccessService:
    def __init__(self, access_reader: AccessReader) -> None:
        self._access_reader = access_reader

    async def has(
        self, user_id: UUID, permission_code: str, location_id: UUID | None = None
    ) -> bool:
        return await self._access_reader.has_permission(
            user_id, permission_code, location_id
        )

    async def require(
        self, user_id: UUID, permission_code: str, location_id: UUID | None = None
    ) -> None:
        if not await self.has(user_id, permission_code, location_id):
            raise ForbiddenError()
