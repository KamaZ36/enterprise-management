from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class Customer:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        first_name: str | None,
        contact_phone: str | None,
        status: CustomerStatus,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._first_name = first_name
        self._contact_phone = contact_phone
        self._status = status
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        user_id: UUID,
        first_name: str | None = None,
        contact_phone: str | None = None,
    ) -> Customer:
        return cls(
            id=uuid7(),
            user_id=user_id,
            first_name=first_name,
            contact_phone=contact_phone,
            status=CustomerStatus.ACTIVE,
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
    def contact_phone(self) -> str | None:
        return self._contact_phone

    @property
    def status(self) -> CustomerStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at
