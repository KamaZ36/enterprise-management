from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.application.errors import IncorrectCredentials
from myasnaya_derevnya.modules.auth.domain.entities.credential import UserCredentialType
from myasnaya_derevnya.modules.auth.domain.entities.identity import UserIdentityType
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.identity.base import (
    UserIdentityRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.services.password_service import PasswordService
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class LoginByPasswordCommand:
    username: str
    password: str


class LoginByPasswordInteractor:
    def __init__(
        self,
        identity_repository: UserIdentityRepository,
        credential_repository: CredentialRepository,
        session_repository: UserSessionRepository,
        transaction_manager: TransactionManager,
        password_service: PasswordService,
    ) -> None:
        self._identity_repository = identity_repository
        self._credential_repository = credential_repository
        self._session_repository = session_repository
        self._transaction_manager = transaction_manager
        self._password_service = password_service

    async def __call__(self, command: LoginByPasswordCommand) -> UUID:
        user_identity = await self._identity_repository.get_by_identifier_and_type(
            identifier=command.username, identity_type=UserIdentityType.USERNAME
        )

        if user_identity is None:
            raise IncorrectCredentials()

        user_credential = await self._credential_repository.get_by_user_id_and_type(
            user_id=user_identity.user_id, credential_type=UserCredentialType.PASSWORD
        )

        if user_credential is None:
            raise IncorrectCredentials()

        if not self._password_service.verify(command.password, user_credential.secret):
            raise IncorrectCredentials()

        session = UserSession.create(
            user_id=user_credential.user_id,
            expires_at=get_datetime_utc() + timedelta(days=30),
        )

        await self._session_repository.add(session)
        await self._transaction_manager.commit()

        return session.id
