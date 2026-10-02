from abc import ABC, abstractmethod

from myasnaya_derevnya.user_service.domain.entities.identity import Identity


class IdentityRepository(ABC):
    @abstractmethod
    async def add(self, identity: Identity) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, identity: Identity) -> None:
        raise NotImplementedError

    @abstractmethod
    async def check_identity_is_exist(self, identifier: str) -> None:
        raise NotImplementedError
