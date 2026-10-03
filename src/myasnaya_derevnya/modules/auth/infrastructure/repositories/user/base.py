from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.auth.domain.entities.user import User


class UserRepository(ABC):
    @abstractmethod
    async def add(self, user: User) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user: User) -> None:
        raise NotImplementedError

    async def get_by_id(self, user_id: UUID) -> User | None:
        raise NotImplementedError
