from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
    StockMovement,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    EmptyMovementError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.utils import get_datetime_utc


def make_movement(
    movement_type: MovementType, quantity: str = "10", total: int = 450000
) -> StockMovement:
    return StockMovement.create(
        occurred_at=get_datetime_utc(),
        warehouse_id=uuid4(),
        nomenclature_id=uuid4(),
        movement_type=movement_type,
        quantity=Decimal(quantity),
        total_cost=Money(kopecks=total),
        posting_id=uuid4(),
    )


def test_receipt_is_positive() -> None:
    movement = make_movement(MovementType.RECEIPT)

    assert movement.quantity == Decimal(10)
    assert movement.total_cost.kopecks == 450000
    assert movement.unit_cost == Decimal(450)


def test_issue_is_negative() -> None:
    movement = make_movement(MovementType.ISSUE, quantity="3", total=138000)

    assert movement.quantity == Decimal(-3)
    assert movement.total_cost.kopecks == -138000
    assert movement.unit_cost == Decimal(460)


def test_write_off_is_negative() -> None:
    movement = make_movement(MovementType.WRITE_OFF, quantity="1", total=45000)

    assert movement.quantity == Decimal(-1)
    assert movement.total_cost.kopecks == -45000


def test_transfer_in_is_positive() -> None:
    movement = make_movement(MovementType.TRANSFER_IN, quantity="2", total=90000)

    assert movement.quantity == Decimal(2)
    assert movement.total_cost.kopecks == 90000


def test_zero_quantity_is_rejected() -> None:
    with pytest.raises(EmptyMovementError):
        make_movement(MovementType.RECEIPT, quantity="0")


def test_negative_quantity_is_rejected() -> None:
    with pytest.raises(EmptyMovementError):
        make_movement(MovementType.RECEIPT, quantity="-5")


def test_posting_reference_is_stored() -> None:
    """Проводка ссылается на проведение, а не на документ: у типа своя таблица."""
    posting_id = uuid4()
    movement = StockMovement.create(
        occurred_at=get_datetime_utc(),
        warehouse_id=uuid4(),
        nomenclature_id=uuid4(),
        movement_type=MovementType.RECEIPT,
        quantity=Decimal(1),
        total_cost=Money(kopecks=100),
        posting_id=posting_id,
    )

    assert movement.posting_id == posting_id


def test_lot_is_optional() -> None:
    movement = make_movement(MovementType.RECEIPT)

    assert movement.lot_id is None


def test_naive_occurred_at_is_rejected() -> None:
    from datetime import datetime

    with pytest.raises(TimezoneRequiredError):
        StockMovement.create(
            occurred_at=datetime(2026, 10, 1, 9, 0),
            warehouse_id=uuid4(),
            nomenclature_id=uuid4(),
            movement_type=MovementType.RECEIPT,
            quantity=Decimal(1),
            total_cost=Money(kopecks=100),
            posting_id=uuid4(),
        )
