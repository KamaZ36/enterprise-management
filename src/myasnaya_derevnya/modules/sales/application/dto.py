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
    fulfillment_type: str = "pickup"
    payment_method: str = "on_pickup"
    payment_status: str = "pending"
    payment_provider: str | None = None
    payment_provider_id: str | None = None
    paid_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class OrderLineItem:
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    unit_price: int
    total: int
    cost_kopecks: int | None = None
    margin: int | None = None


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
    fulfillment_type: str = "pickup"
    payment_method: str = "on_pickup"
    payment_status: str = "pending"
    payment_provider: str | None = None
    payment_provider_id: str | None = None
    paid_at: datetime | None = None
    lines: list[OrderLineItem] = field(default_factory=list)
    cost_total: int | None = None
    margin_total: int | None = None


@dataclass(frozen=True, slots=True)
class CartLine:
    nomenclature_id: UUID
    quantity: Decimal
    unit_price: int
    total: int


@dataclass(frozen=True, slots=True)
class Cart:
    org_unit_id: UUID
    fulfillment_type: str
    payment_method: str
    payment_status: str
    comment: str | None
    total: int
    lines: list[CartLine]
    id: UUID | None = None
