from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.auth.domain.entities.user import User
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)


class CreateUserInteractor:
    def __init__(
        self, user_repository: UserRepository, transaction_manager: TransactionManager
    ) -> None:
        self._user_repository = user_repository
        self._transaction_manager = transaction_manager

    async def __call__(self) -> UUID:
        user = User.create()
        await self._user_repository.add(user)
        return user.id
