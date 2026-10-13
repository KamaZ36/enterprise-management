"""Интеграционные тесты читателей журнала на настоящем PostgreSQL."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.commands import ReceiptLineCommand
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.get import (
    GetReceiptInteractor,
    GetReceiptQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.sqlalchemy import (
    SQLAlchemyReceiptReader,
)
from tests.modules.inventory.helpers import (
    FakeBusinessAPI,
    FakeIdentityProvider,
    FakeStaffAPI,
    build_interactors,
)

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)


async def test_receipt_journal_counts_lines_and_sums_cost(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    first = await make_nomenclature(name="Говядина лопатка", sku="PYTEST-BEEF")
    second = await make_nomenclature(name="Свинина шея", sku="PYTEST-PORK")

    actors = build_interactors(db_session)
    receipt_id = await actors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            supplier_name="Мясокомбинат",
            supplier_document_number="УПД-1042",
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=first.id,
                    quantity=Decimal("40.5"),
                    unit_cost=Decimal("450.5"),
                    lot_code="L-001",
                ),
                ReceiptLineCommand(
                    nomenclature_id=second.id,
                    quantity=Decimal(18),
                    unit_cost=Decimal(610),
                    lot_code="L-002",
                ),
            ],
        )
    )
    await actors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))

    items, total = await SQLAlchemyReceiptReader(db_session).list(
        warehouse_id=warehouse.id
    )

    assert total == 1
    assert items[0].id == receipt_id
    assert items[0].line_count == 2
    assert items[0].total_kopecks == 1824525 + 1098000
    assert items[0].supplier_document_number == "УПД-1042"
    assert items[0].posted_at is not None


async def test_receipt_card_resolves_nomenclature_names(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature(name="Говядина лопатка", sku="PYTEST-BEEF")

    actors = build_interactors(db_session)
    receipt_id = await actors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(10),
                    unit_cost=Decimal("450.5"),
                    lot_code="L-001",
                )
            ],
        )
    )

    interactor = GetReceiptInteractor(
        identity_provider=FakeIdentityProvider(uuid4()),
        receipt_reader=SQLAlchemyReceiptReader(db_session),
        catalog_api=CatalogAPI(SQLAlchemyNomenclatureRepository(db_session)),
        business_api=FakeBusinessAPI(uuid4()),
        staff_api=FakeStaffAPI(),
    )

    detail = await interactor(GetReceiptQuery(receipt_id=receipt_id))

    assert detail.status == "draft"
    assert detail.lines[0].nomenclature_name == "Говядина лопатка"
    assert detail.lines[0].total_kopecks == 450500


async def test_receipt_journal_search_by_supplier_and_document(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    marker = uuid4().hex[:8]
    warehouse = await make_warehouse()
    nomenclature = await make_nomenclature(
        name=f"Позиция {marker}", sku=f"PYTEST-{marker}"
    )

    actors = build_interactors(db_session)
    first_supplier = f"Мясокомбинат {marker}"
    second_supplier = f"Птицефабрика {marker}"

    for supplier, number in (
        (first_supplier, f"УПД-{marker}"),
        (second_supplier, f"ТОРГ-{marker}"),
    ):
        await actors.create_receipt(
            CreateReceiptCommand(
                warehouse_id=warehouse.id,
                occurred_at=OCCURRED_AT,
                supplier_name=supplier,
                supplier_document_number=number,
                lines=[
                    ReceiptLineCommand(
                        nomenclature_id=nomenclature.id,
                        quantity=Decimal(1),
                        unit_cost=Decimal(100),
                    )
                ],
            )
        )

    reader = SQLAlchemyReceiptReader(db_session)

    items, total = await reader.list(search=f"мясокомбинат {marker}", limit=10)
    assert total == 1
    assert [item.supplier_name for item in items] == [first_supplier]

    items, total = await reader.list(search=f"ТОРГ-{marker}", limit=10)
    assert total == 1
    assert [item.supplier_name for item in items] == [second_supplier]

    _, total = await reader.list(search=f"{marker} УПД", limit=10)
    assert total == 1

    _, total = await reader.list(search="такого-поставщика-нет-xyz", limit=10)
    assert total == 0
