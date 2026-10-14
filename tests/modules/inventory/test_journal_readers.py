from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.application.interactors.get_point_prices import (
    GetPointPricesInteractor,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price.sqlalchemy import (
    SQLAlchemyPriceRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.price_list_binding.sqlalchemy import (
    SQLAlchemyPriceListBindingRepository,
)
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.get import (
    GetReceiptInteractor,
    GetReceiptQuery,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.sqlalchemy import (
    SQLAlchemyReceiptReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.transfer.sqlalchemy import (
    SQLAlchemyTransferReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.warehouse.sqlalchemy import (
    SQLAlchemyWarehouseReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.sqlalchemy import (
    SQLAlchemyWriteOffReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.sqlalchemy import (
    SQLAlchemyTransferRepository,
)
from tests.modules.inventory.helpers import (
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
        warehouse_ids=[warehouse.id]
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
        receipt_reader=SQLAlchemyReceiptReader(db_session),
        catalog_api=CatalogAPI(
            get_point_prices_interactor=GetPointPricesInteractor(
                binding_repository=SQLAlchemyPriceListBindingRepository(db_session),
                price_repository=SQLAlchemyPriceRepository(db_session),
            ),
            nomenclature_repository=SQLAlchemyNomenclatureRepository(db_session),
        ),
        document_scope=DocumentScope(
            identity_provider=FakeIdentityProvider(uuid4()),
            warehouse_reader=SQLAlchemyWarehouseReader(db_session),
            staff_api=FakeStaffAPI(),
        ),
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


async def test_receipt_reader_filters_by_allowed_warehouses(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    own = await make_warehouse()
    foreign = await make_warehouse()
    nomenclature = await make_nomenclature()

    actors = build_interactors(db_session)
    own_receipt = await actors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=own.id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                    unit_cost=Decimal(100),
                )
            ],
        )
    )
    await actors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=foreign.id,
            occurred_at=OCCURRED_AT,
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

    items, total = await reader.list(warehouse_ids=[own.id])
    assert total == 1
    assert items[0].id == own_receipt

    _, total = await reader.list(warehouse_ids=[foreign.id])
    assert total == 1

    _, total = await reader.list(warehouse_ids=[])
    assert total == 0


async def test_transfer_reader_filters_and_card_exposes_both_units(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    source_unit, target_unit, foreign_unit = uuid4(), uuid4(), uuid4()
    source = await make_warehouse(org_unit_id=source_unit)
    target = await make_warehouse(org_unit_id=target_unit)
    foreign = await make_warehouse(org_unit_id=foreign_unit)
    nomenclature = await make_nomenclature()

    transfer = Transfer.create(
        from_warehouse_id=source.id,
        to_warehouse_id=target.id,
        occurred_at=OCCURRED_AT,
        lines=[
            TransferLine.create(nomenclature_id=nomenclature.id, quantity=Decimal(3))
        ],
        comment="Перевозка",
    )
    await SQLAlchemyTransferRepository(db_session).add(transfer)
    await db_session.commit()

    reader = SQLAlchemyTransferReader(db_session)

    items, total = await reader.list(warehouse_ids=[source.id])
    assert total == 1
    assert items[0].id == transfer.id

    items, total = await reader.list(warehouse_ids=[target.id])
    assert total == 1
    assert items[0].id == transfer.id

    _, total = await reader.list(warehouse_ids=[foreign.id])
    assert total == 0

    detail = await reader.get(transfer.id)
    assert detail is not None
    assert detail.org_unit_id == source_unit
    assert detail.to_org_unit_id == target_unit


async def test_write_off_card_exposes_warehouse_org_unit(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    org_unit_id = uuid4()
    warehouse = await make_warehouse(org_unit_id=org_unit_id)
    nomenclature = await make_nomenclature()

    actors = build_interactors(db_session)
    write_off_id = await actors.create_write_off(
        CreateWriteOffCommand(
            warehouse_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            reason="Просрочка",
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature.id,
                    quantity=Decimal(1),
                )
            ],
        )
    )

    detail = await SQLAlchemyWriteOffReader(db_session).get(write_off_id)

    assert detail is not None
    assert detail.org_unit_id == org_unit_id
