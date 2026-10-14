from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OrderListItem:
    id: UUID
    number: int | None
    status: str
    channel: str
    org_unit_id: UUID
    customer_id: UUID | None
    created_at: datetime
    planned_at: datetime | None
    total: int
    line_count: int


@dataclass(frozen=True, slots=True)
class OrderLineItem:
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    unit_price: int
    total: int


@dataclass(frozen=True, slots=True)
class OrderDetail:
    id: UUID
    number: int | None
    status: str
    channel: str
    org_unit_id: UUID
    customer_id: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    planned_at: datetime | None
    comment: str | None
    contact_phone: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    total: int
    lines: list[OrderLineItem] = field(default_factory=list)
