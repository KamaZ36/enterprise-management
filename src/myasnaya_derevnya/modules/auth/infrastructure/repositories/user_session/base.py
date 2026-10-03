from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession


class UserSessionRepository(ABC):
    @abstractmethod
    async def add(self, user_session: UserSession) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, user_session_id: UUID) -> UserSession | None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_id(self, user_session_id: UUID) -> None:
        raise NotImplementedError
