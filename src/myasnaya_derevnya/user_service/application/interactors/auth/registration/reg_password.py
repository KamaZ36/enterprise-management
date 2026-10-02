from dataclasses import dataclass

from myasnaya_derevnya.user_service.domain.entities.user import User
from myasnaya_derevnya.user_service.infrastructure.repositories.identity.base import (
    IdentityRepository,
)
from myasnaya_derevnya.user_service.infrastructure.services.password.base import (
    PasswordService,
)


@dataclass
class RegisterPasswordCommand:
    login: str
    password: str


class RegisterPasswordInteractor:
    def __init__(
        self, identity_repository: IdentityRepository, password_service: PasswordService
    ) -> None:
        self._identity_repository = identity_repository
        self._password_serivce = password_service

    async def __call__(self, command: RegisterPasswordCommand) -> None:
        hashed_password = self._password_serivce.hash_password(command.password)

        user = User.create()
