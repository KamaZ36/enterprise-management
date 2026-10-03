from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class LocationType(StrEnum):
    PRODUCTION = "production"
    SHOP = "shop"
    CAFE = "cafe"


class Location:
    def __init__(
        self,
        id: UUID,
        location_type: LocationType,
        name: str,
        code: str,
        address: str | None,
        is_active: bool,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._location_type = location_type
        self._name = name
        self._code = code
        self._address = address
        self._is_active = is_active
        self._created_at = created_at

    @classmethod
    def create(
        cls, location_type: LocationType, name: str, code: str, address: str | None
    ) -> Location:
        name, code = name.strip(), code.strip().lower()
        return cls(
            id=uuid7(),
            location_type=location_type,
            name=name,
            code=code,
            address=address,
            is_active=True,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def location_type(self) -> LocationType:
        return self._location_type

    @property
    def name(self) -> str:
        return self._name

    @property
    def code(self) -> str:
        return self._code

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at
