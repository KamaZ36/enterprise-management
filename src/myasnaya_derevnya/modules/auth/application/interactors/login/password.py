from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.domain.entities.user_session import UserSession
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.services.password_serivce import PasswordService
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class LoginByPasswordCommand:
    username: str
    password: str


class LoginByPasswordInteractor:
    def __init__(
        self,
        credential_repository: CredentialRepository,
        session_repository: UserSessionRepository,
        transaction_manager: TransactionManager,
        password_service: PasswordService,
    ) -> None:
        self._credential_repository = credential_repository
        self._session_repository = session_repository
        self._transaction_manager = transaction_manager
        self._password_service = password_service

    async def __call__(self, command: LoginByPasswordCommand) -> UUID:
        credential = await self._credential_repository.get_by_identifier(
            command.username
        )

        if credential is None or credential.password_hash is None:
            raise ValueError

        if not self._password_service.verify(
            command.password, credential.password_hash
        ):
            raise ValueError

        session = UserSession.create(
            user_id=credential.user_id,
            provider=credential.provider,
            expires_at=get_datetime_utc() + timedelta(days=30),
        )

        await self._session_repository.add(session)
        await self._transaction_manager.commit()

        return session.id
