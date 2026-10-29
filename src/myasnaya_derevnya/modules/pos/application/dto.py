from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PosSourceItem:
    id: UUID
    doka_org_id: str
    name: str
    org_unit_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    org_unit_name: str | None = None


@dataclass(frozen=True, slots=True)
class PosLocationItem:
    id: UUID
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class PosAgentItem:
    id: UUID
    source_id: UUID
    install_id: str | None
    api_key_prefix: str
    hostname: str | None
    version: str | None
    status: str
    pending_receipts: int
    last_seen_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PosAgentKey:
    agent: PosAgentItem
    api_key: str
    api_key_prefix: str


@dataclass(frozen=True, slots=True)
class PosReceiptLineItem:
    id: UUID
    line_number: int
    external_guid: str | None
    product_guid: str
    product_name: str | None
    unit: str | None
    quantity: Decimal
    unit_factor: Decimal
    price_kopecks: int
    amount_kopecks: int
    discount_kopecks: int
    barcode: str | None
    mark_code: str | None
    nomenclature_id: UUID | None
    mapping_status: str
    mapping_error: str | None
    nomenclature_name: str | None = None


@dataclass(frozen=True, slots=True)
class PosReceiptListItem:
    id: UUID
    source_id: UUID
    source_name: str | None
    external_guid: str
    occurred_at: datetime
    kind: str
    payment_kind: str
    total_kopecks: int
    subdivision_name: str | None
    status: str
    error: str | None
    line_count: int
    unmapped_count: int
    posted_at: datetime | None
    org_unit_id: UUID
    org_unit_name: str | None = None


@dataclass(frozen=True, slots=True)
class PosReceiptDetail(PosReceiptListItem):
    subdivision_code: str | None = None
    cashier: str | None = None
    shift: str | None = None
    number: str | None = None
    fd_number: str | None = None
    fp_number: str | None = None
    fn_number: str | None = None
    raw: dict = field(default_factory=dict)
    lines: tuple[PosReceiptLineItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PosReceiptListPage:
    items: tuple[PosReceiptListItem, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class PosProductMappingItem:
    id: UUID
    source_id: UUID
    doka_product_guid: str
    nomenclature_id: UUID
    unit_factor: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    nomenclature_name: str | None = None


@dataclass(frozen=True, slots=True)
class PosUnmappedProductItem:
    """Товар DoKa, который встречается в чеках, но ещё не сопоставлен."""

    product_guid: str
    product_name: str | None
    unit: str | None
    receipts_count: int
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class IncomingReceiptLine:
    guid: str | None
    product_guid: str
    product_name: str | None
    unit: str | None
    quantity: Decimal
    price_kopecks: int
    amount_kopecks: int
    discount_kopecks: int
    barcode: str | None
    mark_code: str | None
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IncomingReceipt:
    guid: str
    occurred_at: datetime
    kind: str
    payment_kind: str
    total_kopecks: int
    subdivision_code: str | None
    subdivision_name: str | None
    cashier: str | None
    shift: str | None
    number: str | None
    fd_number: str | None
    fp_number: str | None
    fn_number: str | None
    warnings: tuple[str, ...] = field(default_factory=tuple)
    lines: tuple[IncomingReceiptLine, ...] = field(default_factory=tuple)
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PosImportReceiptResult:
    guid: str
    status: str
    message: str | None = None


@dataclass(frozen=True, slots=True)
class PosImportResult:
    server_time: datetime
    batch_id: UUID
    results: tuple[PosImportReceiptResult, ...]


@dataclass(frozen=True, slots=True)
class PosPostResult:
    receipt_id: UUID
    status: str
    message: str | None = None


@dataclass(frozen=True, slots=True)
class PosBatchPostResult:
    posted: int
    pending: int
    failed: int
    results: tuple[PosPostResult, ...]


@dataclass(frozen=True, slots=True)
class PosHeartbeatResult:
    server_time: datetime
