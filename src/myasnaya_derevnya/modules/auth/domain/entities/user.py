from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class UserStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class User:
    def __init__(self, id: UUID, created_at: datetime, status: UserStatus) -> None:
        self._id = id
        self._created_at = created_at
        self._status = status

    @classmethod
    def create(cls) -> User:
        return cls(id=uuid7(), created_at=get_datetime_utc(), status=UserStatus.ACTIVE)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def status(self) -> UserStatus:
        return self._status
