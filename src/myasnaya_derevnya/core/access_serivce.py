from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission


class AccessService(ABC):
    @abstractmethod
    async def has_permission(
        self, user_id: UUID, permission: Permission, location_id: UUID | None = None
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def require(
        self, user_id: UUID, permission: Permission, location_id: UUID | None = None
    ) -> None:
        raise NotImplementedError
