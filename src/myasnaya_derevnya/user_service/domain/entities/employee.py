from uuid import UUID, uuid7


class EmployeeProfile:
    def __init__(
        self, id: UUID, user_id: UUID, first_name: str, last_name: str
    ) -> None:
        self._id = id
        self._user_id = user_id
        self._first_name = first_name
        self._last_name = last_name

    @classmethod
    def create(cls, user_id: UUID, first_name: str, last_name: str) -> EmployeeProfile:
        return cls(
            id=uuid7(), user_id=user_id, first_name=first_name, last_name=last_name
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def first_name(self) -> str:
        return self._first_name

    @property
    def last_name(self) -> str:
        return self._last_name

    @property
    def full_name(self) -> str:
        return f"{self._last_name} {self._first_name}"
