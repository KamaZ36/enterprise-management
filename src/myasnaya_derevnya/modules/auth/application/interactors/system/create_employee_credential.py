from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.domain.entities.credential import (
    UserCredential,
    UserCredentialType,
)
from myasnaya_derevnya.modules.auth.domain.entities.identity import (
    UserIdentity,
    UserIdentityType,
)
from myasnaya_derevnya.modules.auth.domain.errors import UserNotFound
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService


@dataclass(frozen=True, slots=True)
class CreateEmployeeCredentialCommand:
    user_id: UUID
    username: str
    password: str


class CreateEmployeeCredentialInteractor:
    def __init__(
        self,
        user_repository: UserRepository,
        identity_repository: UserIdentityRepository,
        credential_repository: CredentialRepository,
        transaction_manager: TransactionManager,
        password_service: PasswordService,
    ) -> None:
        self._user_repository = user_repository
        self._identity_repository = identity_repository
        self._credential_repository = credential_repository
        self._transaction_manager = transaction_manager
        self._password_service = password_service

    async def __call__(self, command: CreateEmployeeCredentialCommand) -> None:
        user = await self._user_repository.get_by_id(user_id=command.user_id)
        if user is None:
            raise UserNotFound()

        user_identity = UserIdentity.create(
            user_id=user.id,
            identity_type=UserIdentityType.USERNAME,
            identifier=command.username,
        )

        password_hash = self._password_service.hash_password(command.password)
        user_credential = UserCredential.create(
            user_id=user.id,
            credential_type=UserCredentialType.PASSWORD,
            secret=password_hash,
        )

        await self._identity_repository.add(user_identity)
        await self._credential_repository.add(user_credential)
