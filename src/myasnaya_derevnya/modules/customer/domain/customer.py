from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class Customer:
    def __init__(
        self, id: UUID, user_id: UUID, first_name: str | None, created_at: datetime
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._first_name = first_name
        self._created_at = created_at

    @classmethod
    def create(cls, user_id: UUID, first_name: str | None) -> Customer:
        return Customer(
            id=uuid7(),
            user_id=user_id,
            first_name=first_name,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def first_name(self) -> str | None:
        return self._first_name

    @property
    def created_at(self) -> datetime:
        return self._created_at
