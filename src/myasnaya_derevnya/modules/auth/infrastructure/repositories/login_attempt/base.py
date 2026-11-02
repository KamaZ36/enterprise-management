from abc import ABC, abstractmethod
from datetime import datetime

from myasnaya_derevnya.modules.auth.domain.entities.login_attempt import LoginAttempt


class LoginAttemptRepository(ABC):
    @abstractmethod
    async def get_by_identifier(self, identifier: str) -> LoginAttempt | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, attempt: LoginAttempt) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_by_identifier(self, identifier: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_stale(self, older_than: datetime) -> int:
        raise NotImplementedError
