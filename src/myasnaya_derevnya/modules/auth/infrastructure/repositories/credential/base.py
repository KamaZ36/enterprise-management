from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.auth.domain.entities.credential import UserCredential


class CredentialRepository(ABC):
    @abstractmethod
    async def add(self, credential: UserCredential) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, credential: UserCredential) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_identifier(self, identifier: str) -> UserCredential | None:
        raise NotImplementedError
