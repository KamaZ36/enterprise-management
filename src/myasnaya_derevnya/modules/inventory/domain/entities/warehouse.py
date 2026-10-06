from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import EmptyWarehouseNameError
from myasnaya_derevnya.utils import get_datetime_utc


class Warehouse:
    def __init__(
        self,
        id_: UUID,
        org_unit_id: UUID,
        name: str,
        code: str,
        is_active: bool,
        created_at: datetime,
        updated_at: datetime,
    ) -> None:
        self._id = id_
        self._org_unit_id = org_unit_id
        self._name = name
        self._code = code
        self._is_active = is_active
        self._created_at = created_at
        self._updated_at = updated_at

    @classmethod
    def create(cls, org_unit_id: UUID, name: str, code: str) -> Warehouse:
        if not name or not name.strip():
            raise EmptyWarehouseNameError()

        return cls(
            id_=uuid7(),
            org_unit_id=org_unit_id,
            name=name,
            code=code,
            is_active=True,
            created_at=get_datetime_utc(),
            updated_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at
