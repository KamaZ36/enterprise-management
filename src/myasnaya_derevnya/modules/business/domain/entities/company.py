from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class Company:
    def __init__(
        self,
        id: UUID,
        org_unit_id: UUID,
        code: str,
        name: str,
        inn: str,
        kpp: str,
        ogrn: str,
        legal_address: str,
        timezone: str,
        is_active: bool,
        attributes: dict,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._org_unit_id = org_unit_id
        self._code = code
        self._name = name
        self._inn = inn
        self._kpp = kpp
        self._ogrn = ogrn
        self._legal_address = legal_address
        self._timezone = timezone
        self._is_active = is_active
        self._attributes = attributes
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        org_unit_id: UUID,
        code: str,
        name: str,
        inn: str,
        kpp: str,
        ogrn: str,
        legal_address: str,
        timezone: str,
        attributes: dict | None = None,
    ) -> Company:
        now = get_datetime_utc()
        return cls(
            id=uuid7(),
            org_unit_id=org_unit_id,
            code=code,
            name=name,
            inn=inn,
            kpp=kpp,
            ogrn=ogrn,
            legal_address=legal_address,
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
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def timezone(self) -> str:
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

    def rename(self, name: str) -> None:
        self._name = name
        self._updated_at = get_datetime_utc()

    def change_timezone(self, timezone: str) -> None:
        self._timezone = timezone
        self._updated_at = get_datetime_utc()

    def change_attributes(self, attributes: dict) -> None:
        self._attributes = attributes
        self._updated_at = get_datetime_utc()

    def deactivate(self) -> None:
        self._is_active = False
        self._updated_at = get_datetime_utc()
