from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.inventory.domain.errors import (
    EmptyMovementError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.utils import get_datetime_utc


class MovementType(StrEnum):
    RECEIPT = "receipt"
    ISSUE = "issue"
    WRITE_OFF = "write_off"
    SALE = "sale"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    INVENTORY_SURPLUS = "inventory_surplus"
    INVENTORY_SHORTAGE = "inventory_shortage"

    PRODUCTION_OUT = "production_out"
    PRODUCTION_IN = "production_in"


INBOUND_TYPES = frozenset(
    {
        MovementType.RECEIPT,
        MovementType.TRANSFER_IN,
        MovementType.INVENTORY_SURPLUS,
        MovementType.PRODUCTION_IN,
    }
)


class StockMovement:
    def __init__(
        self,
        id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
        warehouse_id: UUID,
        nomenclature_id: UUID,
        lot_id: UUID | None,
        movement_type: MovementType,
        quantity: Decimal,
        total_cost: Money,
        posting_id: UUID,
        created_by: UUID | None,
    ) -> None:
        self._id = id
        self._occurred_at = occurred_at
        self._recorded_at = recorded_at
        self._warehouse_id = warehouse_id
        self._nomenclature_id = nomenclature_id
        self._lot_id = lot_id
        self._movement_type = movement_type
        self._quantity = quantity
        self._total_cost = total_cost
        self._posting_id = posting_id
        self._created_by = created_by

    @classmethod
    def create(
        cls,
        *,
        occurred_at: datetime,
        warehouse_id: UUID,
        nomenclature_id: UUID,
        movement_type: MovementType,
        quantity: Decimal,
        total_cost: Money,
        posting_id: UUID,
        lot_id: UUID | None = None,
        created_by: UUID | None = None,
    ) -> StockMovement:
        if quantity <= 0:
            raise EmptyMovementError()
        if occurred_at.tzinfo is None:
            raise TimezoneRequiredError(field="occurred_at")

        direction = 1 if movement_type in INBOUND_TYPES else -1

        return cls(
            id=uuid7(),
            occurred_at=occurred_at,
            recorded_at=get_datetime_utc(),
            warehouse_id=warehouse_id,
            nomenclature_id=nomenclature_id,
            lot_id=lot_id,
            movement_type=movement_type,
            quantity=quantity * direction,
            total_cost=total_cost if direction == 1 else -total_cost,
            posting_id=posting_id,
            created_by=created_by,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    @property
    def recorded_at(self) -> datetime:
        return self._recorded_at

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def nomenclature_id(self) -> UUID:
        return self._nomenclature_id

    @property
    def lot_id(self) -> UUID | None:
        return self._lot_id

    @property
    def movement_type(self) -> MovementType:
        return self._movement_type

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def total_cost(self) -> Money:
        return self._total_cost

    @property
    def unit_cost(self) -> Decimal:
        if self._quantity == 0:
            return Decimal(0)
        return abs(self._total_cost.rubles) / abs(self._quantity)

    @property
    def posting_id(self) -> UUID:
        return self._posting_id

    @property
    def created_by(self) -> UUID | None:
        return self._created_by
