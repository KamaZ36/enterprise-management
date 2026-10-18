from contextvars import ContextVar, Token
from uuid import UUID

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id: ContextVar[UUID | None] = ContextVar("user_id", default=None)


def get_request_id() -> str | None:
    """Идентификатор текущего запроса или ``None`` вне обработки запроса."""
    return _request_id.get()


def set_request_id(value: str | None) -> Token[str | None]:
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def get_user_id() -> UUID | None:
    """Пользователь текущего запроса или ``None``, если он ещё не определён."""
    return _user_id.get()


def set_user_id(value: UUID | None) -> None:
    _user_id.set(value)
