from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


@dataclass(slots=True, eq=False)
class IncorrectCredentials(UnauthorizedError):
    def __str__(self) -> str:
        return "Неверный логин или пароль"


@dataclass(slots=True, eq=False)
class UserNotFound(NotFoundError):
    user_id: UUID

    def __str__(self) -> str:
        return f"Пользователь {self.user_id} не найден."


@dataclass(slots=True, eq=False)
class LoginCodeNotFound(UnauthorizedError):
    def __str__(self) -> str:
        return "Код неверен или истёк"


@dataclass(slots=True, eq=False)
class LoginCodeExpired(UnauthorizedError):
    def __str__(self) -> str:
        return "Код неверен или истёк"


@dataclass(slots=True, eq=False)
class LoginCodeAttemptsExceeded(UnauthorizedError):
    def __str__(self) -> str:
        return "Код неверен или истёк"


@dataclass(slots=True, eq=False)
class LoginCodeInvalid(UnauthorizedError):
    def __str__(self) -> str:
        return "Код неверен или истёк"


@dataclass(slots=True, eq=False)
class LoginCodeRequestTooFrequent(ConflictError):
    retry_after_seconds: int

    def __str__(self) -> str:
        return (
            f"Код уже отправлен. Повторите запрос через {self.retry_after_seconds} с."
        )


@dataclass(slots=True, eq=False)
class InvalidPhoneNumber(ValidationError):
    def __str__(self) -> str:
        return "Укажите телефон в формате +7XXXXXXXXXX"


@dataclass(slots=True, eq=False)
class LoginCodeHourlyLimitExceeded(ConflictError):
    def __str__(self) -> str:
        return "Слишком много запросов кода. Попробуйте позже."
