from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.sales.domain.errors import (
    EmptyOrderLineError,
    NegativePriceError,
    OrderAlreadyClosedError,
    OrderIsNotDraftError,
    OrderStatusTransitionError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.utils import get_datetime_utc


class OrderStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderChannel(StrEnum):
    SITE = "site"
    POS = "pos"
    PHONE = "phone"


TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY, OrderStatus.CANCELLED},
    OrderStatus.READY: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderLine:
    def __init__(
        self,
        id_: UUID,
        nomenclature_id: UUID,
        quantity: Decimal,
        unit_price: int,
    ) -> None:
        self._id = id_
        self._nomenclature_id = nomenclature_id
        self._quantity = quantity
        self._unit_price = unit_price

    @classmethod
    def create(
        cls, nomenclature_id: UUID, quantity: Decimal, unit_price: int
    ) -> OrderLine:
        if quantity <= 0:
            raise EmptyOrderLineError()

        if unit_price < 0:
            raise NegativePriceError()

        return cls(
            id_=uuid7(),
            nomenclature_id=nomenclature_id,
            quantity=quantity,
            unit_price=unit_price,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def unit_price(self) -> int:
        return self._unit_price

    @property
    def total(self) -> int:
        return int(self._quantity * self._unit_price)


class Order:
    def __init__(
        self,
        id_: UUID,
        org_unit_id: UUID,
        channel: OrderChannel,
        created_by: UUID,
        customer_id: UUID | None,
        status: OrderStatus,
        created_at: datetime,
        updated_at: datetime,
        number: int | None = None,
        planned_at: datetime | None = None,
        comment: str | None = None,
        completed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        contact_phone: str | None = None,
        lines: list[OrderLine] | None = None,
    ) -> None:
        self._id = id_
        self._org_unit_id = org_unit_id
        self._channel = channel
        self._created_by = created_by
        self._customer_id = customer_id
        self._status = status
        self._created_at = created_at
        self._updated_at = updated_at
        self._number = number
        self._planned_at = planned_at
        self._comment = comment
        self._completed_at = completed_at
        self._cancelled_at = cancelled_at
        self._contact_phone = contact_phone
        self._lines = lines if lines is not None else []

    @classmethod
    def create(
        cls,
        org_unit_id: UUID,
        channel: OrderChannel,
        created_by: UUID,
        customer_id: UUID | None = None,
        planned_at: datetime | None = None,
        comment: str | None = None,
        contact_phone: str | None = None,
    ) -> Order:
        if planned_at is not None and planned_at.tzinfo is None:
            raise TimezoneRequiredError()

        now = get_datetime_utc()

        return cls(
            id_=uuid7(),
            org_unit_id=org_unit_id,
            channel=channel,
            created_by=created_by,
            customer_id=customer_id,
            status=OrderStatus.DRAFT,
            created_at=now,
            updated_at=now,
            planned_at=planned_at,
            comment=comment,
            contact_phone=contact_phone,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def org_unit_id(self) -> UUID:
        return self._org_unit_id

    @property
    def channel(self) -> OrderChannel:
        return self._channel

    @property
    def created_by(self) -> UUID:
        return self._created_by

    @property
    def customer_id(self) -> UUID | None:
        return self._customer_id

    @property
    def status(self) -> OrderStatus:
        return self._status

    @property
    def number(self) -> int | None:
        return self._number

    @property
    def planned_at(self) -> datetime | None:
        return self._planned_at

    @property
    def comment(self) -> str | None:
        return self._comment

    @property
    def contact_phone(self) -> str | None:
        return self._contact_phone

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @property
    def completed_at(self) -> datetime | None:
        return self._completed_at

    @property
    def cancelled_at(self) -> datetime | None:
        return self._cancelled_at

    @property
    def lines(self) -> list[OrderLine]:
        return list(self._lines)

    @property
    def total(self) -> int:
        return sum(line.total for line in self._lines)

    @property
    def is_editable(self) -> bool:
        return self._status is OrderStatus.DRAFT

    def add_line(
        self, nomenclature_id: UUID, quantity: Decimal, unit_price: int
    ) -> OrderLine:
        if not self.is_editable:
            raise OrderIsNotDraftError()

        line = OrderLine.create(
            nomenclature_id=nomenclature_id, quantity=quantity, unit_price=unit_price
        )
        self._lines.append(line)
        self._touch()

        return line

    def revise(
        self,
        lines: list[tuple[UUID, Decimal, int]],
        planned_at: datetime | None = None,
        comment: str | None = None,
    ) -> None:
        if not self.is_editable:
            raise OrderIsNotDraftError()

        if planned_at is not None and planned_at.tzinfo is None:
            raise TimezoneRequiredError()

        self._lines = [
            OrderLine.create(
                nomenclature_id=nomenclature_id,
                quantity=quantity,
                unit_price=unit_price,
            )
            for nomenclature_id, quantity, unit_price in lines
        ]
        self._planned_at = planned_at
        self._comment = comment
        self._touch()

    def assign_number(self, number: int) -> None:
        self._number = number
        self._touch()

    def set_status(self, status: OrderStatus) -> None:
        if status not in TRANSITIONS[self._status]:
            raise OrderStatusTransitionError(self._status.value, status.value)

        now = get_datetime_utc()
        self._status = status
        self._updated_at = now

        if status is OrderStatus.COMPLETED:
            self._completed_at = now

        if status is OrderStatus.CANCELLED:
            self._cancelled_at = now

    def cancel(self) -> None:
        if self._status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
            raise OrderAlreadyClosedError()

        self.set_status(OrderStatus.CANCELLED)

    def _touch(self) -> None:
        self._updated_at = get_datetime_utc()
