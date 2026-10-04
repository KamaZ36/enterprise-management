from abc import ABC, abstractmethod
from uuid import UUID

from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)


class CredentialRepository(ABC):
    @abstractmethod
    async def add(self, user_credential: UserCredential) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_id_and_type(
        self, user_id: UUID, credential_type: UserCredentialType
    ) -> UserCredential | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, user_credential: UserCredential) -> None:
        raise NotImplementedError
