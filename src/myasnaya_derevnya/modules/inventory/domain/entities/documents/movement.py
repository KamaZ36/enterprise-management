from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.entities.documents.base import DocStatus
from myasnaya_derevnya.utils import get_datetime_utc


class MovementDocumentItem:
    def __init__(self, nomenclature_id: UUID, quantity: Decimal):
        self.nomenclature_id = nomenclature_id
        self.quantity = quantity


class MovementDocument:
    def __init__(
        self,
        id_: UUID,
        doc_number: str,
        source_warehouse_id: UUID,
        target_warehouse_id: UUID,
        status: DocStatus,
        created_at: datetime,
        items: list[MovementDocumentItem],
    ) -> None:
        self._id = id_
        self._doc_number = doc_number
        self._source_warehouse_id = source_warehouse_id
        self._target_warehouse_id = target_warehouse_id
        self._status = status
        self._created_at = created_at
        self._items = items

    @classmethod
    def create(
        cls,
        source_warehouse_id: UUID,
        targret_warehouse_id: UUID,
        status: DocStatus,
        items: list[MovementDocumentItem],
    ) -> MovementDocument:
        return cls(
            id_=uuid7(),
            doc_number="test",
            source_warehouse_id=source_warehouse_id,
            target_warehouse_id=targret_warehouse_id,
            status=status,
            created_at=get_datetime_utc(),
            items=items,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def doc_number(self) -> str:
        return self._doc_number

    @property
    def source_warehouse_id(self) -> UUID:
        return self._source_warehouse_id

    @property
    def target_warehouse_id(self) -> UUID:
        return self._target_warehouse_id

    @property
    def status(self) -> DocStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def items(self) -> list[MovementDocumentItem]:
        return self._items
