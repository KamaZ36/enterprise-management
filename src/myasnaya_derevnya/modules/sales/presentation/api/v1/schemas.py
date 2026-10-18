from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.sales.domain.value_objects.fulfillment import (
    FulfillmentType,
)
from myasnaya_derevnya.modules.sales.domain.value_objects.order_channel import (
    OrderChannel,
)


class OrderListItemSchema(BaseModel):
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
    fulfillment_type: str
    payment_method: str
    payment_status: str
    payment_provider: str | None
    payment_provider_id: str | None
    paid_at: datetime | None

    @classmethod
    def from_dto(cls, item) -> OrderListItemSchema:
        return cls(
            id=item.id,
            number=item.number,
            status=item.status,
            channel=item.channel,
            org_unit_id=item.org_unit_id,
            customer_id=item.customer_id,
            created_at=item.created_at,
            planned_at=item.planned_at,
            total=item.total,
            line_count=item.line_count,
            fulfillment_type=item.fulfillment_type,
            payment_method=item.payment_method,
            payment_status=item.payment_status,
            payment_provider=item.payment_provider,
            payment_provider_id=item.payment_provider_id,
            paid_at=item.paid_at,
        )


class OrderListSchema(BaseModel):
    items: list[OrderListItemSchema]
    total: int


class OrderLineCommandSchema(BaseModel):
    nomenclature_id: UUID
    quantity: Decimal


class CreateOrderSchema(BaseModel):
    org_unit_id: UUID
    channel: OrderChannel
    customer_id: UUID | None = None
    planned_at: datetime | None = None
    comment: str | None = None
    lines: list[OrderLineCommandSchema] = []


class UpdateOrderSchema(BaseModel):
    planned_at: datetime | None = None
    comment: str | None = None
    lines: list[OrderLineCommandSchema] = []


class CreatedOrderSchema(BaseModel):
    order_id: UUID


class OrderLineViewSchema(BaseModel):
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    unit_price: int
    total: int
    cost_kopecks: int | None = None
    margin: int | None = None

    @classmethod
    def from_dto(cls, item) -> OrderLineViewSchema:
        return cls(
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=item.total,
            cost_kopecks=item.cost_kopecks,
            margin=item.margin,
        )


class OrderDetailSchema(BaseModel):
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
    fulfillment_type: str
    payment_method: str
    payment_status: str
    payment_provider: str | None
    payment_provider_id: str | None
    paid_at: datetime | None
    lines: list[OrderLineViewSchema]
    cost_total: int | None = None
    margin_total: int | None = None

    @classmethod
    def from_dto(cls, item) -> OrderDetailSchema:
        return cls(
            id=item.id,
            number=item.number,
            status=item.status,
            channel=item.channel,
            org_unit_id=item.org_unit_id,
            customer_id=item.customer_id,
            created_by=item.created_by,
            created_at=item.created_at,
            updated_at=item.updated_at,
            planned_at=item.planned_at,
            comment=item.comment,
            contact_phone=item.contact_phone,
            completed_at=item.completed_at,
            cancelled_at=item.cancelled_at,
            total=item.total,
            fulfillment_type=item.fulfillment_type,
            payment_method=item.payment_method,
            payment_status=item.payment_status,
            payment_provider=item.payment_provider,
            payment_provider_id=item.payment_provider_id,
            paid_at=item.paid_at,
            lines=[OrderLineViewSchema.from_dto(line) for line in item.lines],
            cost_total=item.cost_total,
            margin_total=item.margin_total,
        )


class MyOrderListItemSchema(BaseModel):
    id: UUID
    number: int | None
    status: str
    channel: str
    org_unit_id: UUID
    created_at: datetime
    planned_at: datetime | None
    total: int
    line_count: int
    fulfillment_type: str
    payment_method: str
    payment_status: str

    @classmethod
    def from_dto(cls, item) -> MyOrderListItemSchema:
        return cls(
            id=item.id,
            number=item.number,
            status=item.status,
            channel=item.channel,
            org_unit_id=item.org_unit_id,
            created_at=item.created_at,
            planned_at=item.planned_at,
            total=item.total,
            line_count=item.line_count,
            fulfillment_type=item.fulfillment_type,
            payment_method=item.payment_method,
            payment_status=item.payment_status,
        )


class MyOrderListSchema(BaseModel):
    items: list[MyOrderListItemSchema]
    total: int


class MyOrderDetailSchema(BaseModel):
    id: UUID
    number: int | None
    status: str
    channel: str
    org_unit_id: UUID
    created_at: datetime
    planned_at: datetime | None
    comment: str | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    total: int
    fulfillment_type: str
    payment_method: str
    payment_status: str
    paid_at: datetime | None
    lines: list[OrderLineViewSchema]

    @classmethod
    def from_dto(cls, item) -> MyOrderDetailSchema:
        return cls(
            id=item.id,
            number=item.number,
            status=item.status,
            channel=item.channel,
            org_unit_id=item.org_unit_id,
            created_at=item.created_at,
            planned_at=item.planned_at,
            comment=item.comment,
            completed_at=item.completed_at,
            cancelled_at=item.cancelled_at,
            total=item.total,
            fulfillment_type=item.fulfillment_type,
            payment_method=item.payment_method,
            payment_status=item.payment_status,
            paid_at=item.paid_at,
            lines=[OrderLineViewSchema.from_dto(line) for line in item.lines],
        )


class CartLineSchema(BaseModel):
    nomenclature_id: UUID
    quantity: Decimal
    unit_price: int
    total: int

    @classmethod
    def from_dto(cls, item) -> CartLineSchema:
        return cls(
            nomenclature_id=item.nomenclature_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=item.total,
        )


class CartSchema(BaseModel):
    id: UUID | None
    org_unit_id: UUID
    fulfillment_type: str
    payment_method: str
    payment_status: str
    comment: str | None
    total: int
    lines: list[CartLineSchema]

    @classmethod
    def from_dto(cls, cart) -> CartSchema:
        return cls(
            id=cart.id,
            org_unit_id=cart.org_unit_id,
            fulfillment_type=cart.fulfillment_type,
            payment_method=cart.payment_method,
            payment_status=cart.payment_status,
            comment=cart.comment,
            total=cart.total,
            lines=[CartLineSchema.from_dto(line) for line in cart.lines],
        )


class UpdateCartSchema(BaseModel):
    org_unit_id: UUID
    fulfillment_type: FulfillmentType = FulfillmentType.PICKUP
    comment: str | None = None
    lines: list[OrderLineCommandSchema] = []


class SubmitCartSchema(BaseModel):
    org_unit_id: UUID
