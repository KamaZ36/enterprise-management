from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class StockBalance:
    def __init__(
        self,
        id_: UUID,
        nomenclature_id: UUID,
        warehouse_id: UUID,
        quantity: Decimal,
        updated_at: datetime,
    ) -> None:
        self._id = id_
        self._nomenclature_id = nomenclature_id
        self._warehouse_id = warehouse_id
        self._quantity = quantity
        self._updated_at = updated_at

    @classmethod
    def create(
        cls, nomenclature_id: UUID, warehouse_id: UUID, quantity: Decimal
    ) -> StockBalance:
        return cls(
            id_=uuid7(),
            nomenclature_id=nomenclature_id,
            warehouse_id=warehouse_id,
            quantity=quantity,
            updated_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def updated_at(self) -> datetime:
        return self._updated_at
