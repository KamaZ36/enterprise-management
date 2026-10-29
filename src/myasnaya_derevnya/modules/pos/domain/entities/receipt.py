from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.pos.domain.errors import (
    EmptyPosTextError,
    InvalidPosAmountError,
    InvalidPosQuantityError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.pos.domain.value_objects.identifiers import (
    canonicalize_guid,
)
from myasnaya_derevnya.utils import get_datetime_utc


class PosReceiptKind(StrEnum):
    SALE = "sale"
    RETURN = "return"


class PosReceiptStatus(StrEnum):
    NEW = "new"
    NEEDS_MAPPING = "needs_mapping"
    READY = "ready"
    NEEDS_STOCK = "needs_stock"
    POSTED = "posted"
    FAILED = "failed"
    IGNORED = "ignored"


class PosLineMappingStatus(StrEnum):
    UNMAPPED = "unmapped"
    MAPPED = "mapped"
    IGNORED = "ignored"


class PosReceiptLine:
    """Строка чека DoKa и её связь с номенклатурой."""

    def __init__(
        self,
        id: UUID,
        receipt_id: UUID,
        line_number: int,
        external_guid: str | None,
        product_guid: str,
        product_name: str | None,
        unit: str | None,
        quantity: Decimal,
        unit_factor: Decimal,
        price_kopecks: int,
        amount_kopecks: int,
        discount_kopecks: int,
        barcode: str | None,
        mark_code: str | None,
        nomenclature_id: UUID | None,
        mapping_status: PosLineMappingStatus,
        mapping_error: str | None,
        raw: dict,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._receipt_id = receipt_id
        self._line_number = line_number
        self._external_guid = external_guid
        self._product_guid = product_guid
        self._product_name = product_name
        self._unit = unit
        self._quantity = quantity
        self._unit_factor = unit_factor
        self._price_kopecks = price_kopecks
        self._amount_kopecks = amount_kopecks
        self._discount_kopecks = discount_kopecks
        self._barcode = barcode
        self._mark_code = mark_code
        self._nomenclature_id = nomenclature_id
        self._mapping_status = mapping_status
        self._mapping_error = mapping_error
        self._raw = raw
        self._created_at = created_at

    @classmethod
    def create(
        cls,
        *,
        receipt_id: UUID,
        line_number: int,
        external_guid: str | None,
        product_guid: str,
        product_name: str | None,
        unit: str | None,
        quantity: Decimal,
        unit_factor: Decimal = Decimal(1),
        price_kopecks: int,
        amount_kopecks: int,
        discount_kopecks: int = 0,
        barcode: str | None = None,
        mark_code: str | None = None,
        raw: dict | None = None,
    ) -> PosReceiptLine:
        if quantity <= 0:
            raise InvalidPosQuantityError()
        if price_kopecks < 0 or amount_kopecks < 0 or discount_kopecks < 0:
            raise InvalidPosAmountError()
        if unit_factor <= 0:
            raise InvalidPosQuantityError()

        return cls(
            id=uuid7(),
            receipt_id=receipt_id,
            line_number=line_number,
            external_guid=(
                canonicalize_guid(external_guid) if external_guid else None
            ),
            product_guid=canonicalize_guid(product_guid),
            product_name=_optional_text(product_name, 512),
            unit=_optional_text(unit, 32),
            quantity=quantity,
            unit_factor=unit_factor,
            price_kopecks=price_kopecks,
            amount_kopecks=amount_kopecks,
            discount_kopecks=discount_kopecks,
            barcode=_optional_text(barcode, 64),
            mark_code=_optional_text(mark_code, 128),
            nomenclature_id=None,
            mapping_status=PosLineMappingStatus.UNMAPPED,
            mapping_error=None,
            raw=raw or {},
            created_at=get_datetime_utc(),
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def receipt_id(self) -> UUID:
        return self._receipt_id

    @property
    def line_number(self) -> int:
        return self._line_number

    @property
    def external_guid(self) -> str | None:
        return self._external_guid

    @property
    def product_guid(self) -> str:
        return self._product_guid

    @property
    def product_name(self) -> str | None:
        return self._product_name

    @property
    def unit(self) -> str | None:
        return self._unit

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def unit_factor(self) -> Decimal:
        return self._unit_factor

    @property
    def price_kopecks(self) -> int:
        return self._price_kopecks

    @property
    def amount_kopecks(self) -> int:
        return self._amount_kopecks

    @property
    def discount_kopecks(self) -> int:
        return self._discount_kopecks

    @property
    def barcode(self) -> str | None:
        return self._barcode

    @property
    def mark_code(self) -> str | None:
        return self._mark_code

    @property
    def nomenclature_id(self) -> UUID | None:
        return self._nomenclature_id

    @property
    def mapping_status(self) -> PosLineMappingStatus:
        return self._mapping_status

    @property
    def mapping_error(self) -> str | None:
        return self._mapping_error

    @property
    def raw(self) -> dict:
        return self._raw

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def is_mapped(self) -> bool:
        return (
            self._mapping_status is PosLineMappingStatus.MAPPED
            and self._nomenclature_id is not None
        )

    def map_to(
        self, nomenclature_id: UUID, *, unit_factor: Decimal | None = None
    ) -> None:
        self._nomenclature_id = nomenclature_id
        self._mapping_status = PosLineMappingStatus.MAPPED
        self._mapping_error = None
        if unit_factor is not None:
            self._unit_factor = unit_factor


class PosReceipt:
    """Чек, полученный из журнала продаж DoKa."""

    def __init__(
        self,
        id: UUID,
        source_id: UUID,
        agent_id: UUID | None,
        batch_id: UUID | None,
        external_guid: str,
        occurred_at: datetime,
        kind: PosReceiptKind,
        payment_kind: str,
        total_kopecks: int,
        subdivision_code: str | None,
        subdivision_name: str | None,
        cashier: str | None,
        shift: str | None,
        number: str | None,
        fd_number: str | None,
        fp_number: str | None,
        fn_number: str | None,
        org_unit_id: UUID,
        status: PosReceiptStatus,
        error: str | None,
        posted_at: datetime | None,
        raw: dict,
        created_at: datetime,
        updated_at: datetime,
        lines: list[PosReceiptLine] | None = None,
    ) -> None:
        self._id = id
        self._source_id = source_id
        self._agent_id = agent_id
        self._batch_id = batch_id
        self._external_guid = external_guid
        self._occurred_at = occurred_at
        self._kind = kind
        self._payment_kind = payment_kind
        self._total_kopecks = total_kopecks
        self._subdivision_code = subdivision_code
        self._subdivision_name = subdivision_name
        self._cashier = cashier
        self._shift = shift
        self._number = number
        self._fd_number = fd_number
        self._fp_number = fp_number
        self._fn_number = fn_number
        self._org_unit_id = org_unit_id
        self._status = status
        self._error = error
        self._posted_at = posted_at
        self._raw = raw
        self._created_at = created_at
        self._updated_at = updated_at
        self._lines = lines if lines is not None else []

    @classmethod
    def create(
        cls,
        *,
        receipt_id: UUID | None = None,
        source_id: UUID,
        agent_id: UUID | None,
        batch_id: UUID | None,
        external_guid: str,
        occurred_at: datetime,
        kind: str,
        payment_kind: str,
        total_kopecks: int,
        subdivision_code: str | None,
        subdivision_name: str | None,
        cashier: str | None,
        shift: str | None,
        number: str | None,
        fd_number: str | None,
        fp_number: str | None,
        fn_number: str | None,
        org_unit_id: UUID,
        lines: list[PosReceiptLine],
        raw: dict | None = None,
    ) -> PosReceipt:
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError()
        if total_kopecks < 0:
            raise InvalidPosAmountError()

        now = get_datetime_utc()
        receipt = cls(
            id=receipt_id or uuid7(),
            source_id=source_id,
            agent_id=agent_id,
            batch_id=batch_id,
            external_guid=canonicalize_guid(external_guid),
            occurred_at=occurred_at,
            kind=PosReceiptKind(kind),
            payment_kind=_required_text(payment_kind, 32),
            total_kopecks=total_kopecks,
            subdivision_code=_optional_text(subdivision_code, 32),
            subdivision_name=_optional_text(subdivision_name, 255),
            cashier=_optional_text(cashier, 255),
            shift=_optional_text(shift, 32),
            number=_optional_text(number, 32),
            fd_number=_optional_text(fd_number, 32),
            fp_number=_optional_text(fp_number, 32),
            fn_number=_optional_text(fn_number, 32),
            org_unit_id=org_unit_id,
            status=PosReceiptStatus.NEW,
            error=None,
            posted_at=None,
            raw=raw or {},
            created_at=now,
            updated_at=now,
            lines=lines,
        )
        receipt.refresh_status()

        return receipt

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def source_id(self) -> UUID:
        return self._source_id

    @property
    def agent_id(self) -> UUID | None:
        return self._agent_id

    @property
    def batch_id(self) -> UUID | None:
        return self._batch_id

    @property
    def external_guid(self) -> str:
        return self._external_guid

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    @property
    def kind(self) -> PosReceiptKind:
        return self._kind

    @property
    def payment_kind(self) -> str:
        return self._payment_kind

    @property
    def total_kopecks(self) -> int:
        return self._total_kopecks

    @property
    def subdivision_code(self) -> str | None:
        return self._subdivision_code

    @property
    def subdivision_name(self) -> str | None:
        return self._subdivision_name

    @property
    def cashier(self) -> str | None:
        return self._cashier

    @property
    def shift(self) -> str | None:
        return self._shift

    @property
    def number(self) -> str | None:
        return self._number

    @property
    def fd_number(self) -> str | None:
        return self._fd_number

    @property
    def fp_number(self) -> str | None:
        return self._fp_number

    @property
    def fn_number(self) -> str | None:
        return self._fn_number

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def status(self) -> PosReceiptStatus:
        return self._status

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def posted_at(self) -> datetime | None:
        return self._posted_at

    @property
    def raw(self) -> dict:
        return self._raw

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def lines(self) -> tuple[PosReceiptLine, ...]:
        return tuple(self._lines)

    @property
    def is_sale(self) -> bool:
        return self._kind is PosReceiptKind.SALE

    @property
    def is_terminal(self) -> bool:
        return self._status in (
            PosReceiptStatus.POSTED,
            PosReceiptStatus.IGNORED,
        )

    @property
    def line_count(self) -> int:
        return len(self._lines)

    @property
    def unmapped_count(self) -> int:
        return sum(1 for line in self._lines if not line.is_mapped)

    @property
    def can_be_posted(self) -> bool:
        return (
            self.is_sale
            and not self.is_terminal
            and bool(self._lines)
            and all(line.is_mapped for line in self._lines)
        )

    def refresh_status(self) -> None:
        if self._status in (
            PosReceiptStatus.POSTED,
            PosReceiptStatus.IGNORED,
        ):
            return

        self._updated_at = get_datetime_utc()

        if not self.is_sale:
            self.mark_ignored(
                "Возврат из DoKa: автоматическое проведение пока не поддерживается."
            )
        elif not self._lines:
            self.mark_ignored("В чеке DoKa нет товарных строк.")
        elif any(not line.is_mapped for line in self._lines):
            self._status = PosReceiptStatus.NEEDS_MAPPING
            self._error = "Есть несопоставленные товары."
        else:
            self._status = PosReceiptStatus.READY
            self._error = None

    def mark_posted(self) -> None:
        now = get_datetime_utc()
        self._status = PosReceiptStatus.POSTED
        self._posted_at = now
        self._error = None
        self._updated_at = now

    def mark_needs_stock(self, error: str) -> None:
        if self._status is PosReceiptStatus.POSTED:
            return

        self._status = PosReceiptStatus.NEEDS_STOCK
        self._error = error[:1024]
        self._updated_at = get_datetime_utc()

    def mark_failed(self, error: str) -> None:
        if self._status is PosReceiptStatus.POSTED:
            return

        self._status = PosReceiptStatus.FAILED
        self._error = error[:1024]
        self._updated_at = get_datetime_utc()

    def mark_ignored(self, reason: str) -> None:
        self._status = PosReceiptStatus.IGNORED
        self._error = reason[:1024]
        self._updated_at = get_datetime_utc()


def _required_text(value: str, limit: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise EmptyPosTextError("payment_kind")

    return normalized[:limit]


def _optional_text(value: str | None, limit: int) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    return normalized[:limit]
