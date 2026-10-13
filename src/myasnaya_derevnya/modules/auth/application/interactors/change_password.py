from dataclasses import dataclass

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.application.errors import IncorrectCredentials
from myasnaya_derevnya.modules.auth.application.services.password_service import (
    PasswordService,
)
from myasnaya_derevnya.modules.auth.domain.entities.credential import UserCredentialType
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    current_password: str
    new_password: str


class ChangePasswordInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        credential_repository: CredentialRepository,
        user_session_repository: UserSessionRepository,
        password_service: PasswordService,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._credential_repository = credential_repository
        self._user_session_repository = user_session_repository
        self._password_service = password_service
        self._transaction_manager = transaction_manager

    async def __call__(self, command: ChangePasswordCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()
        session_id = await self._identity_provider.get_current_session_id()

        credential = await self._credential_repository.get_by_user_id_and_type(
            user_id, UserCredentialType.PASSWORD
        )
        if credential is None or not self._password_service.verify(
            command.current_password, credential.secret
        ):
            raise IncorrectCredentials()

        credential.change_secret(self._password_service.hash(command.new_password))
        await self._credential_repository.save(credential)

        await self._user_session_repository.delete_others_for_user(user_id, session_id)
        await self._transaction_manager.commit()
