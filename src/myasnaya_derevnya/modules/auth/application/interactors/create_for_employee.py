from dataclasses import dataclass

from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)


@dataclass(frozen=True, slots=True)
class CreateUserCommand:
    username: str
    password: str


class CreateUserInteractor:
    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def __call__(self, command: CreateUserCommand) -> None:
        pass
