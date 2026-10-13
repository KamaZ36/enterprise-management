from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    SameWarehouseTransferError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.utils import get_datetime_utc


def make_line(quantity: str = "10") -> TransferLine:
    return TransferLine.create(
        nomenclature_id=uuid4(), quantity=Decimal(quantity), lot_code="LOT-1"
    )


def make_transfer(**kwargs) -> Transfer:
    from_warehouse_id = kwargs.pop("from_warehouse_id", uuid4())
    to_warehouse_id = kwargs.pop("to_warehouse_id", uuid4())

    return Transfer.create(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        occurred_at=kwargs.pop("occurred_at", get_datetime_utc()),
        **kwargs,
    )


def test_new_transfer_is_draft() -> None:
    warehouse_id = uuid4()
    transfer = Transfer.create(
        from_warehouse_id=warehouse_id,
        to_warehouse_id=uuid4(),
        occurred_at=get_datetime_utc(),
        lines=[make_line()],
    )

    assert transfer.is_draft
    assert transfer.posted_at is None
    assert len(transfer.lines) == 1


def test_transfer_to_same_warehouse_is_rejected() -> None:
    warehouse_id = uuid4()

    with pytest.raises(SameWarehouseTransferError):
        Transfer.create(
            from_warehouse_id=warehouse_id,
            to_warehouse_id=warehouse_id,
            occurred_at=get_datetime_utc(),
        )


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(TimezoneRequiredError):
        Transfer.create(
            from_warehouse_id=uuid4(),
            to_warehouse_id=uuid4(),
            occurred_at=datetime(2026, 10, 13, 12, 0),
        )


def test_line_requires_positive_quantity() -> None:
    with pytest.raises(EmptyMovementError):
        TransferLine.create(nomenclature_id=uuid4(), quantity=Decimal(0))


def test_post_requires_lines() -> None:
    transfer = make_transfer()

    with pytest.raises(EmptyDocumentError):
        transfer.post()


def test_posted_transfer_cannot_be_posted_again() -> None:
    transfer = make_transfer(lines=[make_line()])
    transfer.post()

    assert not transfer.is_draft
    assert transfer.posted_at is not None

    with pytest.raises(DocumentAlreadyPostedError):
        transfer.post()


def test_posted_transfer_rejects_new_lines() -> None:
    transfer = make_transfer(lines=[make_line()])
    transfer.post()

    with pytest.raises(DocumentAlreadyPostedError):
        transfer.add_line(make_line())


def test_lines_are_copied_on_read() -> None:
    transfer = make_transfer(lines=[make_line()])

    transfer.lines.clear()
    transfer.lines.append(object())

    assert len(transfer.lines) == 1


def test_posted_at_is_not_in_the_future() -> None:
    transfer = make_transfer(lines=[make_line()])
    transfer.post()

    assert transfer.posted_at is not None
    assert transfer.posted_at <= get_datetime_utc() + timedelta(seconds=1)
