from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.receipt import (
    Receipt,
    ReceiptLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.utils import get_datetime_utc


def make_line(quantity: str = "10", unit_cost: str = "450") -> ReceiptLine:
    return ReceiptLine.create(
        nomenclature_id=uuid4(),
        quantity=Decimal(quantity),
        unit_cost=Decimal(unit_cost),
    )


def make_receipt(lines: list[ReceiptLine] | None = None) -> Receipt:
    return Receipt.create(
        warehouse_id=uuid4(),
        occurred_at=get_datetime_utc(),
        supplier_name="Мясокомбинат",
        supplier_document_number="УПД-42",
        lines=lines if lines is not None else [make_line()],
    )


def test_new_receipt_is_draft() -> None:
    receipt = make_receipt()

    assert receipt.status is DocumentStatus.DRAFT
    assert receipt.is_draft is True
    assert receipt.posted_at is None
    assert receipt.supplier_name == "Мясокомбинат"
    assert receipt.supplier_document_number == "УПД-42"


def test_line_computes_total_cost() -> None:
    line = make_line(quantity="2.5", unit_cost="199.90")

    assert line.total_cost.kopecks == 49975


def test_receipt_total_cost_sums_lines() -> None:
    receipt = make_receipt([make_line("10", "450"), make_line("5", "480")])

    assert receipt.total_cost.kopecks == 450000 + 240000


def test_line_keeps_lot_and_expiry() -> None:
    expires_at = date(2026, 10, 20)
    line = ReceiptLine.create(
        nomenclature_id=uuid4(),
        quantity=Decimal(5),
        unit_cost=Decimal(100),
        lot_code="L-001",
        expires_at=expires_at,
    )

    assert line.lot_code == "L-001"
    assert line.expires_at == expires_at
    assert line.lot_id is None


def test_post_marks_receipt_posted() -> None:
    receipt = make_receipt()

    receipt.post()

    assert receipt.status is DocumentStatus.POSTED
    assert receipt.posted_at is not None
    assert receipt.is_draft is False


def test_second_post_is_rejected() -> None:
    receipt = make_receipt()
    receipt.post()

    with pytest.raises(DocumentAlreadyPostedError):
        receipt.post()


def test_post_without_lines_is_rejected() -> None:
    receipt = make_receipt(lines=[])

    with pytest.raises(EmptyDocumentError):
        receipt.post()


def test_cannot_add_line_to_posted_receipt() -> None:
    receipt = make_receipt()
    receipt.post()

    with pytest.raises(DocumentAlreadyPostedError):
        receipt.add_line(make_line())


def test_line_with_non_positive_quantity_is_rejected() -> None:
    with pytest.raises(EmptyMovementError):
        make_line(quantity="0")

    with pytest.raises(EmptyMovementError):
        make_line(quantity="-1")


def test_naive_occurred_at_is_rejected() -> None:
    with pytest.raises(TimezoneRequiredError):
        Receipt.create(
            warehouse_id=uuid4(),
            occurred_at=datetime(2026, 10, 1, 9, 0),
            lines=[make_line()],
        )


def test_occurred_at_is_independent_from_registration_time() -> None:
    occurred_at = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)

    receipt = Receipt.create(
        warehouse_id=uuid4(), occurred_at=occurred_at, lines=[make_line()]
    )

    assert receipt.occurred_at == occurred_at
    assert receipt.created_at > occurred_at
