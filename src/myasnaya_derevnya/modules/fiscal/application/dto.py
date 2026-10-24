from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CashRegisterListItem:
    id: UUID
    reg_number: str | None
    serial_number: str | None
    name: str
    fiscal_place: str | None
    model: str | None
    fn_number: str | None
    ffd_version: str | None
    company_id: UUID | None
    registered_at: datetime | None
    deregistered_at: datetime | None
    is_active: bool
    org_unit_id: UUID | None = None
    org_unit_name: str | None = None


@dataclass(frozen=True, slots=True)
class CashRegisterBindingItem:
    id: UUID
    org_unit_id: UUID
    effective_from: datetime
    effective_to: datetime | None
    org_unit_name: str | None = None


@dataclass(frozen=True, slots=True)
class CashRegisterDetail(CashRegisterListItem):
    bindings: tuple[CashRegisterBindingItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class StockLocationOption:
    id: UUID
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class OfdReceiptListItem:
    id: UUID
    reg_number: str
    doc_number: int
    fiscal_sign: str
    doc_datetime: datetime
    operation_type: str
    status: str
    total_kopecks: int
    line_count: int
    unmapped_count: int
    org_unit_id: UUID | None = None
    org_unit_name: str | None = None
    error: str | None = None
    posted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OfdReceiptLineItem:
    id: UUID
    line_number: int
    name: str
    barcode: str | None
    quantity: Decimal
    unit: str | None
    price_kopecks: int
    total_kopecks: int
    mapping_status: str
    nomenclature_id: UUID | None = None
    nomenclature_name: str | None = None
    mapping_error: str | None = None


@dataclass(frozen=True, slots=True)
class OfdReceiptDetail(OfdReceiptListItem):
    inn: str = ""
    fn_number: str = ""
    cash_kopecks: int = 0
    ecash_kopecks: int = 0
    is_correction: bool = False
    is_bso: bool = False
    raw: dict = field(default_factory=dict)
    lines: tuple[OfdReceiptLineItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class OfdSyncResult:
    run_id: UUID
    status: str
    receipts_found: int
    receipts_created: int
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OfdPostResult:
    receipt_id: UUID
    status: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OfdBatchPostResult:
    posted: int
    failed: int
    results: tuple[OfdPostResult, ...]


@dataclass(frozen=True, slots=True)
class OfdReceiptListPage:
    items: tuple[OfdReceiptListItem, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class OfdLineMappingResult:
    receipt_id: UUID
    line_id: UUID
    nomenclature_id: UUID
    receipt_status: str
