from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.write_off import (
    WriteOff,
    WriteOffLine,
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


def make_line(quantity: str = "3", lot_code: str | None = None) -> WriteOffLine:
    return WriteOffLine.create(
        nomenclature_id=uuid4(),
        quantity=Decimal(quantity),
        lot_code=lot_code,
    )


def make_write_off(lines: list[WriteOffLine] | None = None) -> WriteOff:
    return WriteOff.create(
        warehouse_id=uuid4(),
        occurred_at=get_datetime_utc(),
        reason="Просрочка",
        comment="Списание по акту",
        lines=lines if lines is not None else [make_line()],
    )


def test_new_write_off_is_draft() -> None:
    write_off = make_write_off()

    assert write_off.status is DocumentStatus.DRAFT
    assert write_off.is_draft is True
    assert write_off.posted_at is None
    assert write_off.reason == "Просрочка"
    assert write_off.comment == "Списание по акту"


def test_line_has_no_cost() -> None:
    """У списания себестоимость определит проведение по средней."""
    line = make_line()

    assert line.quantity == Decimal(3)
    assert not hasattr(line, "total_cost")


def test_line_keeps_lot_reference() -> None:
    line = make_line(lot_code="L-001")

    assert line.lot_code == "L-001"
    assert line.lot_id is None


def test_post_marks_write_off_posted() -> None:
    write_off = make_write_off()

    write_off.post()

    assert write_off.status is DocumentStatus.POSTED
    assert write_off.posted_at is not None


def test_second_post_is_rejected() -> None:
    write_off = make_write_off()
    write_off.post()

    with pytest.raises(DocumentAlreadyPostedError):
        write_off.post()


def test_post_without_lines_is_rejected() -> None:
    write_off = make_write_off(lines=[])

    with pytest.raises(EmptyDocumentError):
        write_off.post()


def test_cannot_add_line_to_posted_document() -> None:
    write_off = make_write_off()
    write_off.post()

    with pytest.raises(DocumentAlreadyPostedError):
        write_off.add_line(make_line())


def test_line_with_non_positive_quantity_is_rejected() -> None:
    with pytest.raises(EmptyMovementError):
        make_line(quantity="0")


def test_naive_occurred_at_is_rejected() -> None:
    with pytest.raises(TimezoneRequiredError):
        WriteOff.create(
            warehouse_id=uuid4(),
            occurred_at=datetime(2026, 10, 1, 9, 0),
            lines=[make_line()],
        )


def test_occurred_at_keeps_timezone() -> None:
    occurred_at = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)

    write_off = WriteOff.create(
        warehouse_id=uuid4(), occurred_at=occurred_at, lines=[make_line()]
    )

    assert write_off.occurred_at == occurred_at
