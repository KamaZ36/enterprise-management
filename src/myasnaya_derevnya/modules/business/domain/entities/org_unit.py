from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.utils import get_datetime_utc


class OrgUnitType(StrEnum):
    ROOT = "root"
    PRODUCTION = "production"
    GROUP = "group"
    CAFE = "cafe"
    SHOP = "shop"
    DEPARTMENT = "department"


class OrgUnit:
    def __init__(
        self,
        id: UUID,
        parent_id: UUID | None,
        type: OrgUnitType,
        code: str,
        name: str,
        address: str | None,
        phone_number: PhoneNumber | None,
        timezone: str | None,
        is_active: bool,
        attributes: dict,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._parent_id = parent_id
        self._type = type
        self._code = code
        self._name = name
        self._address = address
        self._phone_number = phone_number
        self._timezone = timezone
        self._is_active = is_active
        self._attributes = attributes
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create_root(
        cls,
        code: str,
        name: str,
        timezone: str | None = None,
        attributes: dict | None = None,
    ) -> OrgUnit:
        return cls._create(
            parent_id=None,
            type=OrgUnitType.ROOT,
            code=code,
            name=name,
            address=None,
            phone_number=None,
            timezone=timezone,
            attributes=attributes,
        )

    @classmethod
    def create_child(
        cls,
        parent_id: UUID,
        type: OrgUnitType,
        code: str,
        name: str,
        address: str | None = None,
        phone_number: PhoneNumber | None = None,
        timezone: str | None = None,
        attributes: dict | None = None,
    ) -> OrgUnit:
        return cls._create(
            parent_id=parent_id,
            type=type,
            code=code,
            name=name,
            address=address,
            phone_number=phone_number,
            timezone=timezone,
            attributes=attributes,
        )

    @classmethod
    def _create(
        cls,
        parent_id: UUID | None,
        type: OrgUnitType,
        code: str,
        name: str,
        address: str | None,
        phone_number: PhoneNumber | None,
        timezone: str | None,
        attributes: dict | None,
    ) -> OrgUnit:
        now = get_datetime_utc()
        return cls(
            id=uuid7(),
            parent_id=parent_id,
            type=type,
            code=code,
            name=name,
            address=address,
            phone_number=phone_number,
            timezone=timezone,
            is_active=True,
            attributes=attributes or {},
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def parent_id(self) -> UUID | None:
        return self._parent_id

    @property
    def type(self) -> OrgUnitType:
        return self._type

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def address(self) -> str | None:
        return self._address

    @property
    def phone_number(self) -> PhoneNumber | None:
        return self._phone_number

    @property
    def timezone(self) -> str | None:
        return self._timezone

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def attributes(self) -> dict:
        return self._attributes

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def is_root(self) -> bool:
        return self._parent_id is None

    def rename(self, name: str) -> None:
        self._name = name
        self._updated_at = get_datetime_utc()

    def change_attributes(self, attributes: dict) -> None:
        self._attributes = attributes
        self._updated_at = get_datetime_utc()

    def deactivate(self) -> None:
        self._is_active = False
        self._updated_at = get_datetime_utc()
