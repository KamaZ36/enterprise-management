from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReceiptListItem:
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    supplier_name: str | None
    supplier_document_number: str | None
    line_count: int
    total_kopecks: int


@dataclass(frozen=True, slots=True)
class ReceiptLineItem:
    id: UUID
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    total_kopecks: int
    lot_code: str | None
    expires_at: date | None
    nomenclature_name: str | None = None


@dataclass(frozen=True, slots=True)
class ReceiptDetail:
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    supplier_name: str | None
    supplier_document_number: str | None
    comment: str | None
    lines: list[ReceiptLineItem]


@dataclass(frozen=True, slots=True)
class WriteOffListItem:
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    reason: str | None
    line_count: int


@dataclass(frozen=True, slots=True)
class WriteOffLineItem:
    id: UUID
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None
    nomenclature_name: str | None = None


@dataclass(frozen=True, slots=True)
class WriteOffDetail:
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    reason: str | None
    comment: str | None
    lines: list[WriteOffLineItem]


@dataclass(frozen=True, slots=True)
class BalanceListItem:
    org_unit_id: UUID
    nomenclature_id: UUID
    quantity: Decimal
    nomenclature_name: str | None = None
    average_unit_cost: Decimal | None = None
    total_value_kopecks: int | None = None


@dataclass(frozen=True, slots=True)
class LotBalanceListItem:
    org_unit_id: UUID
    nomenclature_id: UUID
    lot_id: UUID
    lot_code: str
    quantity: Decimal
    expires_at: date | None = None
    produced_at: date | None = None
    supplier_name: str | None = None
    nomenclature_name: str | None = None
    unit_cost: Decimal | None = None
    total_value_kopecks: int | None = None


@dataclass(frozen=True, slots=True)
class MovementListItem:
    id: UUID
    occurred_at: datetime
    org_unit_id: UUID
    nomenclature_id: UUID
    movement_type: str
    quantity: Decimal
    lot_id: UUID | None = None
    lot_code: str | None = None
    total_cost_kopecks: int | None = None
    nomenclature_name: str | None = None
    location_name: str | None = None


@dataclass(frozen=True, slots=True)
class LocationListItem:
    id: UUID
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class TransferListItem:
    id: UUID
    from_org_unit_id: UUID
    to_org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    line_count: int


@dataclass(frozen=True, slots=True)
class TransferLineItem:
    id: UUID
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None
    nomenclature_name: str | None = None


@dataclass(frozen=True, slots=True)
class TransferDetail:
    id: UUID
    from_org_unit_id: UUID
    to_org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    lines: list[TransferLineItem]
