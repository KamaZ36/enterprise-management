from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.sales.domain.entities.order import OrderChannel


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


class CreatedOrderSchema(BaseModel):
    order_id: UUID


class OrderLineViewSchema(BaseModel):
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    unit_price: int
    total: int

    @classmethod
    def from_dto(cls, item) -> OrderLineViewSchema:
        return cls(
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total=item.total,
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
    lines: list[OrderLineViewSchema]

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
            lines=[OrderLineViewSchema.from_dto(line) for line in item.lines],
        )


class MyOrderListItemSchema(BaseModel):
    """Строка списка для покупателя: без служебных полей."""

    id: UUID
    number: int | None
    status: str
    channel: str
    org_unit_id: UUID
    created_at: datetime
    planned_at: datetime | None
    total: int
    line_count: int

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
        )


class MyOrderListSchema(BaseModel):
    items: list[MyOrderListItemSchema]
    total: int


class MyOrderDetailSchema(BaseModel):
    """Карточка для покупателя: состав, статус и сумма.

    Сознательно нет того, что клиенту знать не нужно: кто из сотрудников оформил,
    идентификатор профиля, контактный телефон. Отдельная схема — защита от того,
    что служебное поле однажды добавится в общую и утечёт на сайт.
    """

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
            lines=[OrderLineViewSchema.from_dto(line) for line in item.lines],
        )
