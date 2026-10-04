from abc import ABC, abstractmethod

from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)


class UserIdentityRepository(ABC):
    @abstractmethod
    async def add(self, user_identity: UserIdentity) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_identifier_and_type(
        self, identifier: str, identity_type: UserIdentityType
    ) -> UserIdentity | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user_identity: UserIdentity) -> None:
        raise NotImplementedError
