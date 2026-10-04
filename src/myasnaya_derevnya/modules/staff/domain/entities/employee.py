from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.utils import get_datetime_utc


class Employee:
    def __init__(
        self,
        id: UUID,
        user_id: UUID,
        first_name: str,
        last_name: str,
        middle_name: str | None,
        phone_number: PhoneNumber,
        position: str,
        hired_at: date,
        dismissed_at: datetime | None,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._first_name = first_name
        self._last_name = last_name
        self._middle_name = middle_name
        self._phone_number = phone_number
        self._position = position
        self._hired_at = hired_at
        self._dismissed_at = dismissed_at
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        user_id: UUID,
        first_name: str,
        last_name: str,
        middle_name: str | None,
        phone_number: PhoneNumber,
        position: str,
        hired_at: date,
    ) -> Employee:
        return cls(
            id=uuid7(),
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            phone_number=phone_number,
            position=position,
            hired_at=hired_at,
            dismissed_at=None,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def middle_name(self) -> str | None:
        return self._middle_name

    @property
    def phone_number(self) -> PhoneNumber:
        return self._phone_number

    @property
    def position(self) -> str:
        return self._position

    @property
    def hired_at(self) -> date:
        return self._hired_at

    @property
    def dismissed_at(self) -> datetime | None:
        return self._dismissed_at

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def is_active(self) -> bool:
        return self._dismissed_at is None

    def attach_user(self, user_id: UUID) -> None:
        if self._user_id is not None:
            return
        self._user_id = user_id

    def dismiss(self, at: datetime) -> None:
        if self._dismissed_at is not None:
            return
        self._dismissed_at = at
