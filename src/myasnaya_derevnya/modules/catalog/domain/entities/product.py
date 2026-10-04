from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class Product:
    def __init__(
        self,
        id: UUID,
        unit_id: UUID,
        sku: str,
        name: str,
        gtin: str | None,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._unit_id = unit_id
        self._sku = sku
        self._name = name
        self._gtin = gtin
        self._created_at = created_at

    @classmethod
    def create(cls, unit_id: UUID, sku: str, name: str, gtin: str | None) -> Product:
        return cls(
            id=uuid7(),
            unit_id=unit_id,
            sku=sku,
            name=name,
            gtin=gtin,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def sku(self) -> str:
        return self._sku

    @property
    def name(self) -> str:
        return self._name

    @property
    def gtin(self) -> str | None:
        return self._gtin
