from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    DocumentNotPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    NegativeCostError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.utils import get_datetime_utc


@dataclass(frozen=True, slots=True)
class OpeningBalanceLine:
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
        unit_cost: Decimal,
        lot_id: UUID | None = None,
        lot_code: str | None = None,
        expires_at: date | None = None,
    ) -> OpeningBalanceLine:
        if quantity <= 0:
            raise EmptyMovementError()
        if unit_cost < 0:
            raise NegativeCostError()

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


class OpeningBalance:
    """Документ ввода начальных остатков.

    Оприходует товар по указанной себестоимости, партии и сроку годности.
    Используется один раз перед началом учёта, чтобы не заводить фиктивные
    поступления от поставщиков.
    """

    def __init__(
        self,
        id: UUID,
        status: DocumentStatus,
        occurred_at: datetime,
        org_unit_id: UUID,
        comment: str | None,
        created_by: UUID | None,
        created_at: datetime,
        posted_at: datetime | None,
        lines: list[OpeningBalanceLine],
        number: str | None = None,
    ) -> None:
        self._id = id
        self._status = status
        self._number = number
        self._occurred_at = occurred_at
        self._org_unit_id = org_unit_id
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
        lines: list[OpeningBalanceLine] | None = None,
        created_by: UUID | None = None,
        comment: str | None = None,
        number: str | None = None,
    ) -> OpeningBalance:
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        return cls(
            id=uuid7(),
            status=DocumentStatus.DRAFT,
            occurred_at=occurred_at,
            org_unit_id=org_unit_id,
            comment=comment,
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
    def lines(self) -> list[OpeningBalanceLine]:
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

    def add_line(self, line: OpeningBalanceLine) -> None:
        if not self.is_draft:
            raise DocumentAlreadyPostedError(self._id)
        self._lines.append(line)

    def revise(
        self,
        *,
        occurred_at: datetime,
        comment: str | None,
        lines: list[OpeningBalanceLine],
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

    def unpost(self) -> None:
        if self._status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(self._id)

        self._status = DocumentStatus.DRAFT
        self._posted_at = None

