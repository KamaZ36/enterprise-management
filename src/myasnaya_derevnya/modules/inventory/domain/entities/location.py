from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class LocationType(StrEnum):
    RETAIL_STORE = "store"
    CAFE = "cafe"
    PRODUCTION_PLANT = "plant"


class Location:
    def __init__(
        self,
        id: UUID,
        name: str,
        location_type: LocationType,
        address: str,
        is_active: bool,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._name = name
        self._location_type = location_type
        self._address = address
        self._is_active = is_active
        self._created_at = created_at

    @classmethod
    def create(cls, name: str, location_type: LocationType, address: str) -> Location:
        return cls(
            id=uuid7(),
            name=name,
            location_type=location_type,
            address=address,
            is_active=True,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def location_type(self) -> LocationType:
        return self._location_type

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at
