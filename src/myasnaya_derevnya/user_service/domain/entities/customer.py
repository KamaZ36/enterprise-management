from datetime import date
from uuid import UUID, uuid7


class CustomerProfile:
    def __init__(
        self, id: UUID, user_id: UUID, phone: str, birth_date: date | None
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._phone = phone
        self._birth_date = birth_date

    @classmethod
    def create(cls, user_id: UUID, phone: str, birth_date: date) -> CustomerProfile:
        return cls(id=uuid7(), user_id=user_id, phone=phone, birth_date=birth_date)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def phone(self) -> str:
        return self._phone

    @property
    def birth_date(self) -> date | None:
        return self._birth_date
