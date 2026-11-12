from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.inventory.domain.entities.shipment import (
    Shipment,
    ShipmentLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    DocumentNotPostedError,
    EmptyDocumentError,
    EmptyMovementError,
    EmptyShipmentRecipientError,
    TimezoneRequiredError,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.utils import get_datetime_utc


def make_line(quantity: str = "3", lot_code: str | None = None) -> ShipmentLine:
    return ShipmentLine.create(
        nomenclature_id=uuid4(),
        quantity=Decimal(quantity),
        lot_code=lot_code,
    )


def make_shipment(lines: list[ShipmentLine] | None = None) -> Shipment:
    return Shipment.create(
        org_unit_id=uuid4(),
        occurred_at=get_datetime_utc(),
        recipient="Магазин на Ленина",
        comment="Ежедневная отгрузка",
        lines=lines if lines is not None else [make_line()],
    )


def test_new_shipment_is_draft() -> None:
    shipment = make_shipment()

    assert shipment.status is DocumentStatus.DRAFT
    assert shipment.is_draft is True
    assert shipment.posted_at is None
    assert shipment.recipient == "Магазин на Ленина"
    assert shipment.comment == "Ежедневная отгрузка"


def test_recipient_is_trimmed() -> None:
    shipment = Shipment.create(
        org_unit_id=uuid4(),
        occurred_at=get_datetime_utc(),
        recipient="  Кафе Центральное  ",
    )

    assert shipment.recipient == "Кафе Центральное"


def test_empty_recipient_is_rejected() -> None:
    with pytest.raises(EmptyShipmentRecipientError):
        Shipment.create(
            org_unit_id=uuid4(),
            occurred_at=get_datetime_utc(),
            recipient="   ",
        )


def test_shipment_requires_timezone() -> None:
    with pytest.raises(TimezoneRequiredError):
        Shipment.create(
            org_unit_id=uuid4(),
            occurred_at=datetime(2026, 11, 12, 10, 0),
            recipient="Магазин",
        )


def test_line_rejects_empty_quantity() -> None:
    with pytest.raises(EmptyMovementError):
        ShipmentLine.create(nomenclature_id=uuid4(), quantity=Decimal(0))


def test_post_marks_shipment_posted() -> None:
    shipment = make_shipment()

    shipment.post()

    assert shipment.status is DocumentStatus.POSTED
    assert shipment.posted_at is not None


def test_second_post_is_rejected() -> None:
    shipment = make_shipment()
    shipment.post()

    with pytest.raises(DocumentAlreadyPostedError):
        shipment.post()


def test_post_without_lines_is_rejected() -> None:
    shipment = make_shipment(lines=[])

    with pytest.raises(EmptyDocumentError):
        shipment.post()


def test_unpost_returns_shipment_to_draft() -> None:
    shipment = make_shipment()
    shipment.post()

    shipment.unpost()

    assert shipment.status is DocumentStatus.DRAFT
    assert shipment.posted_at is None


def test_unpost_of_draft_is_rejected() -> None:
    shipment = make_shipment()

    with pytest.raises(DocumentNotPostedError):
        shipment.unpost()


def test_cannot_add_line_to_posted_document() -> None:
    shipment = make_shipment()
    shipment.post()

    with pytest.raises(DocumentAlreadyPostedError):
        shipment.add_line(make_line())


def test_revise_replaces_header_and_lines() -> None:
    shipment = make_shipment([make_line("3")])

    shipment.revise(
        occurred_at=datetime(2026, 11, 12, 9, 0, tzinfo=UTC),
        recipient="Магазин Северный",
        comment="Уточнили состав",
        lines=[make_line("1", "L-9")],
    )

    assert shipment.recipient == "Магазин Северный"
    assert shipment.comment == "Уточнили состав"
    assert [line.quantity for line in shipment.lines] == [Decimal(1)]
    assert shipment.lines[0].lot_code == "L-9"


def test_revise_of_posted_shipment_is_rejected() -> None:
    shipment = make_shipment()
    shipment.post()

    with pytest.raises(DocumentAlreadyPostedError):
        shipment.revise(
            occurred_at=get_datetime_utc(),
            recipient="Магазин",
            comment=None,
            lines=[make_line()],
        )
