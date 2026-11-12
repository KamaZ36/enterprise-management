from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    DocumentNotPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    EmptyShipmentRecipientError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.utils import get_datetime_utc

RECIPIENT_MAX_LENGTH = 255
COMMENT_MAX_LENGTH = 512


@dataclass(frozen=True, slots=True)
class ShipmentLine:
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
    ) -> ShipmentLine:
        if quantity <= 0:
            raise EmptyMovementError()

        return cls(
            id=uuid7(),
            nomenclature_id=nomenclature_id,
            quantity=quantity,
            lot_id=lot_id,
            lot_code=lot_code,
        )


class Shipment:
    """Отгрузка со склада внешнему получателю.

    В отличие от перемещения, на другом конце остаток не появляется:
    получатель (магазин, точка, контрагент) не ведёт склад в системе.
    Поэтому движение только расходное, а куда уехал товар — фиксируется
    текстом в поле ``recipient``.
    """

    def __init__(
        self,
        id: UUID,
        status: DocumentStatus,
        occurred_at: datetime,
        org_unit_id: UUID,
        recipient: str,
        comment: str | None,
        created_by: UUID | None,
        created_at: datetime,
        posted_at: datetime | None,
        lines: list[ShipmentLine],
        number: str | None = None,
    ) -> None:
        self._id = id
        self._status = status
        self._number = number
        self._occurred_at = occurred_at
        self._org_unit_id = org_unit_id
        self._recipient = recipient
        self._comment = comment
        self._created_by = created_by
        self._created_at = created_at
        self._posted_at = posted_at
        self._lines = lines

    @classmethod
    def create(
        cls,
        org_unit_id: UUID,
        occurred_at: datetime,
        recipient: str,
        lines: list[ShipmentLine] | None = None,
        created_by: UUID | None = None,
        comment: str | None = None,
        number: str | None = None,
    ) -> Shipment:
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        return cls(
            id=uuid7(),
            status=DocumentStatus.DRAFT,
            occurred_at=occurred_at,
            org_unit_id=org_unit_id,
            recipient=_normalize_recipient(recipient),
            comment=_normalize_comment(comment),
            created_by=created_by,
            created_at=get_datetime_utc(),
            posted_at=None,
            lines=list(lines or []),
            number=number,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def number(self) -> str | None:
        return self._number

    @property
    def status(self) -> DocumentStatus:
        return self._status

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def recipient(self) -> str:
        return self._recipient

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
    def lines(self) -> list[ShipmentLine]:
        return list(self._lines)

    @property
    def is_draft(self) -> bool:
        return self._status is DocumentStatus.DRAFT

    def add_line(self, line: ShipmentLine) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        self._lines.append(line)

    def revise(
        self,
        *,
        occurred_at: datetime,
        recipient: str,
        comment: str | None,
        lines: list[ShipmentLine],
    ) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)

        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        self._occurred_at = occurred_at
        self._recipient = _normalize_recipient(recipient)
        self._comment = _normalize_comment(comment)
        self._lines = list(lines)

    def post(self) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        if not self._lines:
            raise EmptyDocumentError(self._id)

        self._status = DocumentStatus.POSTED
        self._posted_at = get_datetime_utc()

    def unpost(self) -> None:
        if self._status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(self._id)

        self._status = DocumentStatus.DRAFT
        self._posted_at = None


def _normalize_recipient(recipient: str) -> str:
    cleaned = (recipient or "").strip()
    if not cleaned:
        raise EmptyShipmentRecipientError()

    return cleaned[:RECIPIENT_MAX_LENGTH]


def _normalize_comment(comment: str | None) -> str | None:
    cleaned = (comment or "").strip()

    return cleaned[:COMMENT_MAX_LENGTH] or None
