from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.utils import get_datetime_utc


class StockMovement:
    def __init__(
        self,
        id_: UUID,
        nomenclature_id: UUID,
        warehouse_id: UUID,
        document_id: UUID,
        quantity_change: Decimal,
        created_at: datetime,
    ) -> None:
        self._id = id_
        self._nomenclature_id = nomenclature_id
        self._warehouse_id = warehouse_id
        self._document_id = document_id
        self._quantity_change = quantity_change
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        nomenclature_id: UUID,
        warehouse_id: UUID,
        document_id: UUID,
        quantity_change: Decimal,
    ) -> StockMovement:
        return cls(
            id_=uuid7(),
            nomenclature_id=nomenclature_id,
            warehouse_id=warehouse_id,
            document_id=document_id,
            quantity_change=quantity_change,
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def document_id(self) -> UUID:
        return self._document_id

    @property
    def created_at(self) -> datetime:
        return self._created_at
