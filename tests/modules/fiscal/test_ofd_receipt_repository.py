from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_product_alias import (
    OfdProductAlias,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdReceipt,
    OfdReceiptLine,
    OfdReceiptStatus,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.sqlalchemy import (
    SQLAlchemyOfdReceiptReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.sqlalchemy import (
    SQLAlchemyOfdReceiptRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db

REG_NUMBER = "0000000000051264"
_UNSET = object()


def build_receipt(
    *,
    doc_number: int = 1,
    fiscal_sign: str | None = None,
    org_unit_id: object = _UNSET,
):
    receipt_id = uuid4()
    line = OfdReceiptLine.create(
        receipt_id=receipt_id,
        line_number=1,
        name=f"{TEST_PREFIX}Кофе",
        barcode=f"{TEST_PREFIX}4600000000017",
        product_code={},
        quantity=Decimal(1),
        unit="0",
        price_kopecks=13000,
        total_kopecks=13000,
        raw={"Name": f"{TEST_PREFIX}Кофе"},
    )
    receipt = OfdReceipt.create(
        receipt_id=receipt_id,
        inn="2308139496",
        reg_number=REG_NUMBER,
        fn_number="9999078902009926",
        doc_number=doc_number,
        fiscal_sign=fiscal_sign or f"{TEST_PREFIX}{doc_number}",
        raw_id=f"{TEST_PREFIX}raw-{doc_number}",
        doc_datetime=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        c_date_utc=datetime(2026, 10, 24, 9, 1, tzinfo=UTC),
        operation_type="Income",
        is_correction=False,
        is_bso=False,
        total_kopecks=13000,
        cash_kopecks=13000,
        ecash_kopecks=0,
        org_unit_id=uuid4() if org_unit_id is _UNSET else org_unit_id,
        lines=[line],
        raw={"DocNumber": doc_number},
    )
    return receipt, line


async def test_repository_is_idempotent_by_fiscal_identity(db_session) -> None:
    repository = SQLAlchemyOfdReceiptRepository(db_session)
    receipt, line = build_receipt()

    assert await repository.add_if_absent(receipt) is True
    await db_session.commit()

    duplicate, _ = build_receipt()
    # Тот же фискальный документ, но другой локальный id.
    duplicate._doc_number = receipt.doc_number
    duplicate._fiscal_sign = receipt.fiscal_sign
    duplicate._fn_number = receipt.fn_number
    duplicate._reg_number = receipt.reg_number
    assert await repository.add_if_absent(duplicate) is False

    loaded = await repository.get_by_id(receipt.id)
    assert loaded is not None
    assert loaded.status is OfdReceiptStatus.NEEDS_MAPPING
    assert len(loaded.lines) == 1
    assert loaded.lines[0].id == line.id

    by_line = await repository.get_by_line_id(line.id)
    assert by_line is not None
    assert by_line.id == receipt.id


async def test_reader_lists_and_returns_detail(db_session) -> None:
    repository = SQLAlchemyOfdReceiptRepository(db_session)
    reader = SQLAlchemyOfdReceiptReader(db_session)
    receipt, _ = build_receipt(doc_number=2)

    await repository.add_if_absent(receipt)
    await db_session.commit()

    items, total = await reader.list(
        status=OfdReceiptStatus.NEEDS_MAPPING.value,
        reg_number=REG_NUMBER,
        date_from=None,
        date_to=None,
        org_unit_ids=None,
        limit=10,
        offset=0,
    )
    assert total == 1
    assert items[0].id == receipt.id
    assert items[0].line_count == 1
    assert items[0].unmapped_count == 1

    detail = await reader.get(receipt.id)
    assert detail is not None
    assert detail.fn_number == receipt.fn_number
    assert detail.lines[0].name == f"{TEST_PREFIX}Кофе"


async def test_mapping_changes_status_and_alias_is_upserted(db_session) -> None:
    repository = SQLAlchemyOfdReceiptRepository(db_session)
    receipt, line = build_receipt(doc_number=3)
    nomenclature_id = uuid4()

    await repository.add_if_absent(receipt)
    await db_session.commit()

    loaded = await repository.get_by_id(receipt.id)
    assert loaded is not None
    loaded.map_line(line.id, nomenclature_id)
    await repository.save_line(loaded.lines[0])
    await repository.save(loaded)

    await repository.save_alias(
        OfdProductAlias.create(
            barcode=line.barcode or "",
            nomenclature_id=nomenclature_id,
            created_by=None,
        )
    )
    await db_session.commit()

    reloaded = await repository.get_by_id(receipt.id)
    assert reloaded is not None
    assert reloaded.status is OfdReceiptStatus.READY
    assert reloaded.lines[0].nomenclature_id == nomenclature_id

    alias = await repository.alias_by_barcode(line.barcode or "")
    assert alias is not None
    assert alias.nomenclature_id == nomenclature_id


async def test_needs_location_receipts_can_be_repaired(db_session) -> None:
    repository = SQLAlchemyOfdReceiptRepository(db_session)
    receipt, _ = build_receipt(doc_number=9, org_unit_id=None)
    assert receipt.status is OfdReceiptStatus.NEEDS_LOCATION

    await repository.add_if_absent(receipt)
    await db_session.commit()

    waiting = await repository.needs_location_receipts(REG_NUMBER)
    assert [item.id for item in waiting] == [receipt.id]

    receipt.set_location(uuid4())
    await repository.save(receipt)
    await db_session.commit()

    assert await repository.needs_location_receipts(REG_NUMBER) == []
