from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosLineMappingStatus,
    PosReceipt,
    PosReceiptKind,
    PosReceiptLine,
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.domain.errors import (
    InvalidPosAmountError,
    InvalidPosQuantityError,
    TimezoneRequiredError,
)

OCCURRED_AT = datetime(2026, 10, 24, 8, 2, 26, tzinfo=UTC)
SOURCE_ID = uuid4()
ORG_UNIT_ID = uuid4()
RECEIPT_GUID = "27DE775614AD4D17A482B578611C605C915612757914"


def build_line(*, receipt_id, quantity: Decimal = Decimal(1), number: int = 1):
    return PosReceiptLine.create(
        receipt_id=receipt_id,
        line_number=number,
        external_guid=None,
        product_guid="A0F13AA47AF4468F8CD2EF7CF14E3674",
        product_name="Медовик",
        unit="кг",
        quantity=quantity,
        price_kopecks=25000,
        amount_kopecks=25000,
    )


def build_receipt(*, kind: str = "sale", lines=None, occurred_at=OCCURRED_AT):
    receipt_id = uuid4()
    receipt_lines = (
        lines
        if lines is not None
        else [build_line(receipt_id=receipt_id)]
    )

    return PosReceipt.create(
        receipt_id=receipt_id,
        source_id=SOURCE_ID,
        agent_id=None,
        batch_id=None,
        external_guid=RECEIPT_GUID,
        occurred_at=occurred_at,
        kind=kind,
        payment_kind="card",
        total_kopecks=25000,
        subdivision_code="1",
        subdivision_name="Торговый зал",
        cashier="Администратор",
        shift="422",
        number="1",
        fd_number="18747",
        fp_number="1603810978",
        fn_number="7380440902472099",
        org_unit_id=ORG_UNIT_ID,
        lines=receipt_lines,
    )


def test_new_receipt_with_unmapped_lines_needs_mapping() -> None:
    receipt = build_receipt()

    assert receipt.status is PosReceiptStatus.NEEDS_MAPPING
    assert receipt.unmapped_count == 1
    assert receipt.can_be_posted is False


def test_mapped_receipt_becomes_ready() -> None:
    receipt = build_receipt()
    receipt.lines[0].map_to(uuid4())

    receipt.refresh_status()

    assert receipt.status is PosReceiptStatus.READY
    assert receipt.unmapped_count == 0
    assert receipt.can_be_posted is True


def test_receipt_without_lines_is_ignored() -> None:
    receipt = build_receipt(lines=[])

    assert receipt.status is PosReceiptStatus.IGNORED
    assert receipt.error is not None


def test_return_receipt_is_ignored() -> None:
    receipt = build_receipt(kind="return")

    assert receipt.kind is PosReceiptKind.RETURN
    assert receipt.status is PosReceiptStatus.IGNORED


def test_mapping_sets_factor_and_status() -> None:
    receipt = build_receipt()
    line = receipt.lines[0]

    line.map_to(uuid4(), unit_factor=Decimal("0.001"))

    assert line.mapping_status is PosLineMappingStatus.MAPPED
    assert line.unit_factor == Decimal("0.001")
    assert line.is_mapped is True


def test_posted_receipt_is_terminal_and_not_reopened() -> None:
    receipt = build_receipt()
    receipt.lines[0].map_to(uuid4())
    receipt.refresh_status()
    receipt.mark_posted()

    receipt.refresh_status()

    assert receipt.status is PosReceiptStatus.POSTED
    assert receipt.can_be_posted is False
    assert receipt.posted_at is not None


def test_needs_stock_can_be_retried() -> None:
    receipt = build_receipt()
    receipt.lines[0].map_to(uuid4())
    receipt.refresh_status()
    receipt.mark_needs_stock("Нет остатка")

    assert receipt.status is PosReceiptStatus.NEEDS_STOCK
    assert receipt.error == "Нет остатка"


def test_receipt_rejects_naive_time_and_negative_totals() -> None:
    with pytest.raises(TimezoneRequiredError):
        build_receipt(occurred_at=datetime(2026, 10, 24, 8, 2, 26))

    receipt_id = uuid4()
    with pytest.raises(InvalidPosAmountError):
        PosReceipt.create(
            receipt_id=receipt_id,
            source_id=SOURCE_ID,
            agent_id=None,
            batch_id=None,
            external_guid=RECEIPT_GUID,
            occurred_at=OCCURRED_AT,
            kind="sale",
            payment_kind="card",
            total_kopecks=-1,
            subdivision_code=None,
            subdivision_name=None,
            cashier=None,
            shift=None,
            number=None,
            fd_number=None,
            fp_number=None,
            fn_number=None,
            org_unit_id=ORG_UNIT_ID,
            lines=[],
        )


def test_line_rejects_non_positive_quantity() -> None:
    with pytest.raises(InvalidPosQuantityError):
        PosReceiptLine.create(
            receipt_id=uuid4(),
            line_number=1,
            external_guid=None,
            product_guid="A0F13AA47AF4468F8CD2EF7CF14E3674",
            product_name="Медовик",
            unit="кг",
            quantity=Decimal(0),
            price_kopecks=25000,
            amount_kopecks=25000,
        )
