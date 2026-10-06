from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class PriceList:
    def __init__(self, id_: UUID, name: str, created_at: datetime) -> None:
        self._id = id_
        self._name = name
        self._created_at = created_at

    @classmethod
    def create(cls, name: str) -> PriceList:
        return cls(id_=uuid7(), name=name, created_at=get_datetime_utc())

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def created_at(self) -> datetime:
        return self._created_at
