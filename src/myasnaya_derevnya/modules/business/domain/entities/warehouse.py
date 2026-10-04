from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class Warehouse:
    def __init__(
        self, id: UUID, location_id: UUID, name: str, created_at: datetime
    ) -> None:
        self._id = id
        self._location_id = location_id
        self._name = name
        self._created_at = created_at

    @classmethod
    def create(cls, location_id: UUID, name: str) -> Warehouse:
        return cls(
            id=uuid7(),
            location_id=location_id,
            name=name,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def location_id(self) -> UUID:
        return self._location_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at
