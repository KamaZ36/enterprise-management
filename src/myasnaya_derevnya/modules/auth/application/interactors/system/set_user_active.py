import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.auth.application.errors import UserNotFound
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user.base import (
    UserRepository,
)
from myasnaya_derevnya.modules.auth.infrastructure.repositories.user_session.base import (
    UserSessionRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SetUserActiveCommand:
    user_id: UUID
    is_active: bool


class SetUserActiveInteractor:
    """Блокировка/разблокировка пользователя.

    При блокировке все сессии пользователя удаляются, чтобы уже выданный
    токен перестал работать немедленно. Коммит транзакции выполняет вызывающий
    сценарий — так блокировка и, например, увольнение сотрудника попадают
    в одну транзакцию.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: UserSessionRepository,
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository

    async def __call__(self, command: SetUserActiveCommand) -> None:
        user = await self._user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFound(command.user_id)

        if command.is_active:
            user.unblock()
        else:
            user.block()
            await self._session_repository.delete_all_for_user(user.id)

        await self._user_repository.save(user)

        event = (
            "Пользователь разблокирован"
            if command.is_active
            else "Пользователь заблокирован"
        )
        logger.info(event, extra={"target_user_id": str(user.id)})
