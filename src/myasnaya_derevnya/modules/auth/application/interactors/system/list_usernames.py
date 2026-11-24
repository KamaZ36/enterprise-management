from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.auth.infrastructure.readers.username.base import (
    UsernameReader,
)


@dataclass(frozen=True, slots=True)
class ListUsernamesQuery:
    user_ids: frozenset[UUID]


class ListUsernamesInteractor:
    """Возвращает логины пользователей, чтобы показать их в интерфейсе."""

    def __init__(self, reader: UsernameReader) -> None:
        self._reader = reader

    async def __call__(self, query: ListUsernamesQuery) -> dict[UUID, str]:
        return await self._reader.usernames_for_users(query.user_ids)
