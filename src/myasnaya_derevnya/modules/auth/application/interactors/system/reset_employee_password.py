from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.auth.application.errors import UserNotFound
from myasnaya_derevnya.modules.auth.domain.entities.credential import UserCredentialType
from myasnaya_derevnya.modules.auth.infrastructure.repositories.credential.base import (
    CredentialRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)
from myasnaya_derevnya.modules.auth.services.password_service import PasswordService


@dataclass(frozen=True, slots=True)
class ResetEmployeePasswordCommand:
    user_id: UUID
    password: str


class ResetEmployeePasswordInteractor:
    def __init__(
        self,
        credential_repository: CredentialRepository,
        user_session_repository: UserSessionRepository,
        password_service: PasswordService,
    ) -> None:
        self._credential_repository = credential_repository
        self._user_session_repository = user_session_repository
        self._password_service = password_service

    async def __call__(self, command: ResetEmployeePasswordCommand) -> None:
        credential = await self._credential_repository.get_by_user_id_and_type(
            command.user_id, UserCredentialType.PASSWORD
        )
        if credential is None:
            raise UserNotFound(command.user_id)

        credential.change_secret(self._password_service.hash(command.password))
        await self._credential_repository.save(credential)

        await self._user_session_repository.delete_all_for_user(command.user_id)
