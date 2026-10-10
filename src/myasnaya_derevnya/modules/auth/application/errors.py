from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import NotFoundError, UnauthorizedError


@dataclass(slots=True, eq=False)
class IncorrectCredentials(UnauthorizedError):
    def __str__(self) -> str:
        return "Неверный логин или пароль"


@dataclass(slots=True, eq=False)
class UserNotFound(NotFoundError):
    user_id: UUID

    def __str__(self) -> str:
        return f"Пользователь {self.user_id} не найден."
