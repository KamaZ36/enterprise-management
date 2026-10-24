from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import AsyncClient

from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdReceipt,
    OfdReceiptLine,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.sqlalchemy import (
    SQLAlchemyOfdReceiptRepository,
)
from tests.modules.helpers import TEST_PREFIX

pytestmark = pytest.mark.db

REG_NUMBER = "0000000000051264"


async def _create_receipt(
    db_session, org_unit_id
) -> tuple[OfdReceipt, OfdReceiptLine]:
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
        doc_number=42,
        fiscal_sign=f"{TEST_PREFIX}42",
        raw_id=f"{TEST_PREFIX}raw-42",
        doc_datetime=datetime(2026, 10, 24, 9, 0, tzinfo=UTC),
        c_date_utc=datetime(2026, 10, 24, 9, 1, tzinfo=UTC),
        operation_type="Income",
        is_correction=False,
        is_bso=False,
        total_kopecks=13000,
        cash_kopecks=13000,
        ecash_kopecks=0,
        org_unit_id=org_unit_id,
        lines=[line],
        raw={"DocNumber": 42},
    )
    repository = SQLAlchemyOfdReceiptRepository(db_session)
    await repository.add_if_absent(receipt)
    await db_session.commit()
    return receipt, line


async def test_list_and_detail_receipts(
    client: AsyncClient, db_session, root_org_unit_id
) -> None:
    receipt, line = await _create_receipt(db_session, root_org_unit_id)

    response = await client.get(
        "/api/fiscal/ofd/receipts",
        params={"status": "needs_mapping", "reg_number": REG_NUMBER},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == str(receipt.id)
    assert payload["items"][0]["unmapped_count"] == 1

    response = await client.get(f"/api/fiscal/ofd/receipts/{receipt.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["fiscal_sign"] == receipt.fiscal_sign
    assert payload["lines"][0]["id"] == str(line.id)
    assert payload["lines"][0]["mapping_status"] == "unmapped"


async def test_map_line_endpoint(
    client: AsyncClient, db_session, make_nomenclature, root_org_unit_id
) -> None:
    receipt, line = await _create_receipt(db_session, root_org_unit_id)
    nomenclature = await make_nomenclature()

    response = await client.post(
        f"/api/fiscal/ofd/lines/{line.id}/map",
        json={
            "nomenclature_id": str(nomenclature.id),
            "remember_barcode": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["receipt_status"] == "ready"

    response = await client.get(f"/api/fiscal/ofd/receipts/{receipt.id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["lines"][0]["nomenclature_id"] == str(nomenclature.id)
    assert payload["lines"][0]["nomenclature_name"] == nomenclature.name


async def test_sync_rejects_invalid_period(client: AsyncClient) -> None:
    response = await client.post(
        "/api/fiscal/ofd/receipts/sync",
        json={
            "reg_number": REG_NUMBER,
            "date_from": "2026-10-24T12:00:00",
            "date_to": "2026-10-24T12:00:00",
        },
    )
    assert response.status_code == 422
