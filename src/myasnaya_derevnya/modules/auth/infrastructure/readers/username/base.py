from abc import ABC, abstractmethod
from collections.abc import Collection
from uuid import UUID


class UsernameReader(ABC):
    @abstractmethod
    async def usernames_for_users(
        self, user_ids: Collection[UUID]
    ) -> dict[UUID, str]:
        """Логины пользователей по их идентификаторам."""
        raise NotImplementedError
