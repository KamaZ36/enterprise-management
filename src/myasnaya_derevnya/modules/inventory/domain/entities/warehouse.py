from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import EmptyFieldError
from myasnaya_derevnya.utils import get_datetime_utc


class WarehouseType(StrEnum):
    RAW = "raw"
    PRODUCTION = "production"
    FINISHED = "finished"
    SHOP = "shop"


class Warehouse:
    def __init__(
        self,
        id: UUID,
        org_unit_id: UUID,
        code: str,
        name: str,
        type: WarehouseType,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id
        self._org_unit_id = org_unit_id
        self._code = code
        self._name = name
        self._type = type
        self._is_active = is_active
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(
        cls,
        org_unit_id: UUID,
        code: str,
        name: str,
        type: WarehouseType,
    ) -> Warehouse:
        if not code.strip():
            raise EmptyFieldError(field="code")
        if not name.strip():
            raise EmptyFieldError(field="name")

        now = get_datetime_utc()
        return cls(
            id=uuid7(),
            org_unit_id=org_unit_id,
            code=code,
            name=name,
            type=type,
            is_active=True,
            created_at=now,
            updated_at=now,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def code(self) -> str:
        return self._code

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> WarehouseType:
        return self._type

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def rename(self, name: str) -> None:
        if not name.strip():
            raise EmptyFieldError(field="name")
        self._name = name
        self._updated_at = get_datetime_utc()

    def change_type(self, type_: WarehouseType) -> None:
        self._type = type_
        self._updated_at = get_datetime_utc()

    def deactivate(self) -> None:
        self._is_active = False
        self._updated_at = get_datetime_utc()

    def activate(self) -> None:
        self._is_active = True
        self._updated_at = get_datetime_utc()
