from dataclasses import dataclass
from datetime import datetime
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
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class WriteOffLine:
    """Строка списания: цены нет, себестоимость определит проведение.

    Партия указывается ссылкой на существующую.
    """

    id: UUID
    nomenclature_id: UUID
    quantity: Decimal
    lot_id: UUID | None
    lot_code: str | None

    @classmethod
    def create(
        cls,
        nomenclature_id: UUID,
        quantity: Decimal,
        lot_id: UUID | None = None,
        lot_code: str | None = None,
    ) -> WriteOffLine:
        if quantity <= 0:
            raise EmptyMovementError()

        return cls(
            id=uuid7(),
            nomenclature_id=nomenclature_id,
            quantity=quantity,
            lot_id=lot_id,
            lot_code=lot_code,
        )


class WriteOff:
    """Списание: просрочка, брак, недостача."""

    def __init__(
        self,
        id: UUID,
        status: DocumentStatus,
        occurred_at: datetime,
        warehouse_id: UUID,
        reason: str | None,
        comment: str | None,
        created_by: UUID | None,
        created_at: datetime,
        posted_at: datetime | None,
        lines: list[WriteOffLine],
    ) -> None:
        self._id = id
        self._status = status
        self._occurred_at = occurred_at
        self._warehouse_id = warehouse_id
        self._reason = reason
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
        lines: list[WriteOffLine] | None = None,
        created_by: UUID | None = None,
        reason: str | None = None,
        comment: str | None = None,
    ) -> WriteOff:
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        return cls(
            id=uuid7(),
            status=DocumentStatus.DRAFT,
            occurred_at=occurred_at,
            warehouse_id=warehouse_id,
            reason=reason,
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
    def reason(self) -> str | None:
        return self._reason

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
    def lines(self) -> list[WriteOffLine]:
        return list(self._lines)

    @property
    def is_draft(self) -> bool:
        return self._status is DocumentStatus.DRAFT

    def add_line(self, line: WriteOffLine) -> None:
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
