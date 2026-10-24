from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.fiscal.domain.errors import (
    InvalidOfdQuantityError,
    OfdReceiptLineNotFoundError,
    OfdReceiptNotPostableError,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.barcode import (
    normalize_barcode,
)
from myasnaya_derevnya.utils import get_datetime_utc


class OfdReceiptStatus(StrEnum):
    NEW = "new"
    NEEDS_LOCATION = "needs_location"
    NEEDS_MAPPING = "needs_mapping"
    READY = "ready"
    POSTED = "posted"
    FAILED = "failed"
    IGNORED = "ignored"


class OfdLineMappingStatus(StrEnum):
    UNMAPPED = "unmapped"
    MAPPED = "mapped"
    IGNORED = "ignored"


class OfdReceiptLine:
    """Строка чека ОФД и её связь с номенклатурой."""

    def __init__(
        self,
        id: UUID,
        receipt_id: UUID,
        line_number: int,
        name: str,
        barcode: str | None,
        product_code: dict,
        quantity: Decimal,
        unit: str | None,
        price_kopecks: int,
        total_kopecks: int,
        nomenclature_id: UUID | None,
        mapping_status: OfdLineMappingStatus,
        mapping_error: str | None,
        raw: dict,
        created_at: datetime,
    ) -> None:
        self._id = id
        self._receipt_id = receipt_id
        self._line_number = line_number
        self._name = name
        self._barcode = barcode
        self._product_code = product_code
        self._quantity = quantity
        self._unit = unit
        self._price_kopecks = price_kopecks
        self._total_kopecks = total_kopecks
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
        name: str,
        barcode: str | None,
        product_code: dict | None,
        quantity: Decimal,
        unit: str | None,
        price_kopecks: int,
        total_kopecks: int,
        raw: dict,
    ) -> OfdReceiptLine:
        if quantity <= 0:
            raise InvalidOfdQuantityError()

        return cls(
            id=uuid7(),
            receipt_id=receipt_id,
            line_number=line_number,
            name=name.strip(),
            barcode=normalize_barcode(barcode),
            product_code=product_code or {},
            quantity=quantity,
            unit=unit,
            price_kopecks=price_kopecks,
            total_kopecks=total_kopecks,
            nomenclature_id=None,
            mapping_status=OfdLineMappingStatus.UNMAPPED,
            mapping_error=None,
            raw=raw,
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
    def name(self) -> str:
        return self._name

    @property
    def barcode(self) -> str | None:
        return self._barcode

    @property
    def product_code(self) -> dict:
        return self._product_code

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def unit(self) -> str | None:
        return self._unit

    @property
    def price_kopecks(self) -> int:
        return self._price_kopecks

    @property
    def total_kopecks(self) -> int:
        return self._total_kopecks

    @property
    def nomenclature_id(self) -> UUID | None:
        return self._nomenclature_id

    @property
    def mapping_status(self) -> OfdLineMappingStatus:
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
            self._mapping_status is OfdLineMappingStatus.MAPPED
            and self._nomenclature_id is not None
        )

    def map_to(self, nomenclature_id: UUID) -> None:
        self._nomenclature_id = nomenclature_id
        self._mapping_status = OfdLineMappingStatus.MAPPED
        self._mapping_error = None

    def ignore(self, reason: str | None = None) -> None:
        self._nomenclature_id = None
        self._mapping_status = OfdLineMappingStatus.IGNORED
        self._mapping_error = reason


class OfdReceipt:
    """Сохранённый чек ОФД.

    Чек неизменяем по фискальным данным. Меняются только статус, привязка
    строк к номенклатуре и отметка о проведении.
    """

    def __init__(
        self,
        id: UUID,
        inn: str,
        reg_number: str,
        fn_number: str,
        doc_number: int,
        fiscal_sign: str,
        raw_id: str | None,
        doc_datetime: datetime,
        c_date_utc: datetime | None,
        operation_type: str,
        is_correction: bool,
        is_bso: bool,
        total_kopecks: int,
        cash_kopecks: int,
        ecash_kopecks: int,
        org_unit_id: UUID | None,
        status: OfdReceiptStatus,
        error: str | None,
        posted_at: datetime | None,
        posted_by: UUID | None,
        raw: dict,
        created_at: datetime,
        updated_at: datetime,
        lines: list[OfdReceiptLine] | None = None,
    ) -> None:
        self._id = id
        self._inn = inn
        self._reg_number = reg_number
        self._fn_number = fn_number
        self._doc_number = doc_number
        self._fiscal_sign = fiscal_sign
        self._raw_id = raw_id
        self._doc_datetime = doc_datetime
        self._c_date_utc = c_date_utc
        self._operation_type = operation_type
        self._is_correction = is_correction
        self._is_bso = is_bso
        self._total_kopecks = total_kopecks
        self._cash_kopecks = cash_kopecks
        self._ecash_kopecks = ecash_kopecks
        self._org_unit_id = org_unit_id
        self._status = status
        self._error = error
        self._posted_at = posted_at
        self._posted_by = posted_by
        self._raw = raw
        self._created_at = created_at
        self._updated_at = updated_at
        self._lines = lines if lines is not None else []

    @classmethod
    def create(
        cls,
        *,
        inn: str,
        reg_number: str,
        fn_number: str,
        doc_number: int,
        fiscal_sign: str,
        raw_id: str | None,
        doc_datetime: datetime,
        c_date_utc: datetime | None,
        operation_type: str,
        is_correction: bool,
        is_bso: bool,
        total_kopecks: int,
        cash_kopecks: int,
        ecash_kopecks: int,
        org_unit_id: UUID | None,
        lines: list[OfdReceiptLine],
        raw: dict,
        receipt_id: UUID | None = None,
    ) -> OfdReceipt:
        now = get_datetime_utc()
        receipt = cls(
            id=receipt_id or uuid7(),
            inn=inn,
            reg_number=reg_number,
            fn_number=fn_number,
            doc_number=doc_number,
            fiscal_sign=fiscal_sign,
            raw_id=raw_id,
            doc_datetime=doc_datetime,
            c_date_utc=c_date_utc,
            operation_type=operation_type,
            is_correction=is_correction,
            is_bso=is_bso,
            total_kopecks=total_kopecks,
            cash_kopecks=cash_kopecks,
            ecash_kopecks=ecash_kopecks,
            org_unit_id=org_unit_id,
            status=OfdReceiptStatus.NEW,
            error=None,
            posted_at=None,
            posted_by=None,
            raw=raw,
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
    def inn(self) -> str:
        return self._inn

    @property
    def reg_number(self) -> str:
        return self._reg_number

    @property
    def fn_number(self) -> str:
        return self._fn_number

    @property
    def doc_number(self) -> int:
        return self._doc_number

    @property
    def fiscal_sign(self) -> str:
        return self._fiscal_sign

    @property
    def raw_id(self) -> str | None:
        return self._raw_id

    @property
    def doc_datetime(self) -> datetime:
        return self._doc_datetime

    @property
    def c_date_utc(self) -> datetime | None:
        return self._c_date_utc

    @property
    def operation_type(self) -> str:
        return self._operation_type

    @property
    def is_correction(self) -> bool:
        return self._is_correction

    @property
    def is_bso(self) -> bool:
        return self._is_bso

    @property
    def total_kopecks(self) -> int:
        return self._total_kopecks

    @property
    def cash_kopecks(self) -> int:
        return self._cash_kopecks

    @property
    def ecash_kopecks(self) -> int:
        return self._ecash_kopecks

    @property
    def org_unit_id(self) -> UUID | None:
        return self._org_unit_id

    @property
    def status(self) -> OfdReceiptStatus:
        return self._status

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def posted_at(self) -> datetime | None:
        return self._posted_at

    @property
    def posted_by(self) -> UUID | None:
        return self._posted_by

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
    def lines(self) -> tuple[OfdReceiptLine, ...]:
        return tuple(self._lines)

    @property
    def unmapped_count(self) -> int:
        return sum(1 for line in self._lines if not line.is_mapped)

    @property
    def is_income(self) -> bool:
        return self._operation_type.strip().lower() == "income"

    @property
    def can_be_posted(self) -> bool:
        return (
            self._status is OfdReceiptStatus.READY
            and self._org_unit_id is not None
            and bool(self._lines)
            and all(line.is_mapped for line in self._lines)
        )

    def refresh_status(self) -> None:
        if self._status in (OfdReceiptStatus.POSTED, OfdReceiptStatus.IGNORED):
            return

        if not self.is_income or self._is_correction or self._is_bso:
            self._status = OfdReceiptStatus.IGNORED
            self._error = "Возврат, коррекция или БСО обрабатываются вручную."
        elif self._org_unit_id is None:
            self._status = OfdReceiptStatus.NEEDS_LOCATION
            self._error = "Касса не привязана к складу на дату чека."
        elif not self._lines:
            self._status = OfdReceiptStatus.IGNORED
            self._error = "В чеке нет товарных строк."
        elif any(not line.is_mapped for line in self._lines):
            self._status = OfdReceiptStatus.NEEDS_MAPPING
            self._error = "Есть несопоставленные товары."
        else:
            self._status = OfdReceiptStatus.READY
            self._error = None

        self._updated_at = get_datetime_utc()

    def set_location(self, org_unit_id: UUID | None) -> None:
        self._org_unit_id = org_unit_id
        self.refresh_status()

    def line(self, line_id: UUID) -> OfdReceiptLine:
        for line in self._lines:
            if line.id == line_id:
                return line

        raise OfdReceiptLineNotFoundError(self._id, line_id)

    def map_line(self, line_id: UUID, nomenclature_id: UUID) -> None:
        if self._status is OfdReceiptStatus.POSTED:
            raise OfdReceiptNotPostableError(self._id, "чек уже проведён.")
        if self._status is OfdReceiptStatus.IGNORED:
            raise OfdReceiptNotPostableError(
                self._id, "чек обрабатывается вручную."
            )

        self.line(line_id).map_to(nomenclature_id)
        self.refresh_status()

    def ensure_postable(self) -> None:
        if self._status is OfdReceiptStatus.POSTED:
            raise OfdReceiptNotPostableError(self._id, "чек уже проведён.")
        if self._status is OfdReceiptStatus.IGNORED:
            raise OfdReceiptNotPostableError(
                self._id, "чек помечен как обрабатываемый вручную."
            )
        if self._org_unit_id is None:
            raise OfdReceiptNotPostableError(
                self._id, "не определён склад по кассе."
            )
        if not self._lines:
            raise OfdReceiptNotPostableError(self._id, "в чеке нет строк.")
        if any(not line.is_mapped for line in self._lines):
            raise OfdReceiptNotPostableError(
                self._id, "не все товары сопоставлены с номенклатурой."
            )

    def mark_posted(self, *, posted_by: UUID | None) -> None:
        self._status = OfdReceiptStatus.POSTED
        self._posted_at = get_datetime_utc()
        self._posted_by = posted_by
        self._error = None
        self._updated_at = get_datetime_utc()

    def mark_failed(self, error: str) -> None:
        if self._status is OfdReceiptStatus.POSTED:
            return

        self._status = OfdReceiptStatus.FAILED
        self._error = error[:1024]
        self._updated_at = get_datetime_utc()

    def mark_ignored(self, reason: str) -> None:
        self._status = OfdReceiptStatus.IGNORED
        self._error = reason[:1024]
        self._updated_at = get_datetime_utc()
