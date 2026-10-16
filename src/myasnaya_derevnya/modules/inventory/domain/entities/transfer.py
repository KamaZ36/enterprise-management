from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    SameLocationTransferError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class TransferLine:
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
    ) -> TransferLine:
        if quantity <= 0:
            raise EmptyMovementError()

        return cls(
            id=uuid7(),
            nomenclature_id=nomenclature_id,
            quantity=quantity,
            lot_id=lot_id,
            lot_code=lot_code,
        )


class Transfer:
    def __init__(
        self,
        id: UUID,
        status: DocumentStatus,
        occurred_at: datetime,
        from_org_unit_id: UUID,
        to_org_unit_id: UUID,
        comment: str | None,
        created_by: UUID | None,
        created_at: datetime,
        posted_at: datetime | None,
        lines: list[TransferLine],
    ) -> None:
        self._id = id
        self._status = status
        self._occurred_at = occurred_at
        self._from_org_unit_id = from_org_unit_id
        self._to_org_unit_id = to_org_unit_id
        self._comment = comment
        self._created_by = created_by
        self._created_at = created_at
        self._posted_at = posted_at
        self._lines = lines

    @classmethod
    def create(
        cls,
        from_org_unit_id: UUID,
        to_org_unit_id: UUID,
        occurred_at: datetime,
        lines: list[TransferLine] | None = None,
        created_by: UUID | None = None,
        comment: str | None = None,
    ) -> Transfer:
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        if from_org_unit_id == to_org_unit_id:
            raise SameLocationTransferError(from_org_unit_id)

        return cls(
            id=uuid7(),
            status=DocumentStatus.DRAFT,
            occurred_at=occurred_at,
            from_org_unit_id=from_org_unit_id,
            to_org_unit_id=to_org_unit_id,
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
    def from_org_unit_id(self) -> UUID:
        return self._from_org_unit_id

    @property
    def to_org_unit_id(self) -> UUID:
        return self._to_org_unit_id

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
    def lines(self) -> list[TransferLine]:
        return list(self._lines)

    @property
    def is_draft(self) -> bool:
        return self._status is DocumentStatus.DRAFT

    def add_line(self, line: TransferLine) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        self._lines.append(line)

    def revise(
        self,
        *,
        occurred_at: datetime,
        comment: str | None,
        lines: list[TransferLine],
    ) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)

        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        self._occurred_at = occurred_at
        self._comment = comment
        self._lines = list(lines)

    def post(self) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        if not self._lines:
            raise EmptyDocumentError(self._id)

        self._status = DocumentStatus.POSTED
        self._posted_at = get_datetime_utc()
