from abc import ABC, abstractmethod
from uuid import UUID


class AccessReader(ABC):
    @abstractmethod
    async def has_permission(
        self, user_id: UUID, permission_code: str, location_id: UUID | None
    ) -> bool:
        raise NotImplementedError
