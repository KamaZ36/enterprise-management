from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class ReceiptLine:
    """Строка поступления: сколько привезли и по какой цене."""

    id: UUID
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Money
    lot_id: UUID | None
    lot_code: str | None
    expires_at: date | None

    @classmethod
    def create(
        cls,
        nomenclature_id: UUID,
        quantity: Decimal,
        unit_cost: Decimal = Decimal(0),
        lot_id: UUID | None = None,
        lot_code: str | None = None,
        expires_at: date | None = None,
    ) -> ReceiptLine:
        if quantity <= 0:
            raise EmptyMovementError()

        return cls(
            id=uuid7(),
            nomenclature_id=nomenclature_id,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=Money.from_quantity_and_unit_cost(quantity, unit_cost),
            lot_id=lot_id,
            lot_code=lot_code,
            expires_at=expires_at,
        )


class Receipt:
    """Поступление от поставщика: партию можно завести, если её ещё нет."""

    def __init__(
        self,
        id: UUID,
        status: DocumentStatus,
        occurred_at: datetime,
        warehouse_id: UUID,
        supplier_name: str | None,
        supplier_document_number: str | None,
        comment: str | None,
        created_by: UUID | None,
        created_at: datetime,
        posted_at: datetime | None,
        lines: list[ReceiptLine],
    ) -> None:
        self._id = id
        self._status = status
        self._occurred_at = occurred_at
        self._warehouse_id = warehouse_id
        self._supplier_name = supplier_name
        self._supplier_document_number = supplier_document_number
        self._comment = comment
        self._created_by = created_by
        self._created_at = created_at
        self._posted_at = posted_at
        self._lines = lines

    @classmethod
    def create(
        cls,
        warehouse_id: UUID,
        occurred_at: datetime,
        lines: list[ReceiptLine] | None = None,
        created_by: UUID | None = None,
        supplier_name: str | None = None,
        supplier_document_number: str | None = None,
        comment: str | None = None,
    ) -> Receipt:
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        return cls(
            id=uuid7(),
            status=DocumentStatus.DRAFT,
            occurred_at=occurred_at,
            warehouse_id=warehouse_id,
            supplier_name=supplier_name,
            supplier_document_number=supplier_document_number,
            comment=comment,
            created_by=created_by,
            created_at=get_datetime_utc(),
            posted_at=None,
            lines=list(lines or []),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def status(self) -> DocumentStatus:
        return self._status

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def supplier_name(self) -> str | None:
        return self._supplier_name

    @property
    def supplier_document_number(self) -> str | None:
        return self._supplier_document_number

    @property
    def comment(self) -> str | None:
        return self._comment

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def posted_at(self) -> datetime | None:
        return self._posted_at

    @property
    def lines(self) -> list[ReceiptLine]:
        return list(self._lines)

    @property
    def is_draft(self) -> bool:
        return self._status is DocumentStatus.DRAFT

    @property
    def total_cost(self) -> Money:
        total = Money.zero()
        for line in self._lines:
            total = total + line.total_cost
        return total

    def add_line(self, line: ReceiptLine) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        self._lines.append(line)

    def post(self) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        if not self._lines:
            raise EmptyDocumentError(self._id)

        self._status = DocumentStatus.POSTED
        self._posted_at = get_datetime_utc()
