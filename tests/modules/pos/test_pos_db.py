from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.sqlalchemy import (
    SQLAlchemyStockPostingRepository,
)
from myasnaya_derevnya.modules.pos.application.dto import (
    IncomingReceipt,
    IncomingReceiptLine,
)
from myasnaya_derevnya.modules.pos.application.interactors.import_receipts import (
    ImportPosReceiptsCommand,
    ImportPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent
from myasnaya_derevnya.modules.pos.domain.entities.product_mapping import (
    PosProductMapping,
)
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceipt,
    PosReceiptLine,
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.domain.value_objects.api_key import (
    api_key_prefix,
    generate_api_key,
    hash_api_key,
)
from myasnaya_derevnya.modules.pos.infrastructure.readers.product_map.sqlalchemy import (
    SQLAlchemyPosProductMapReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.sqlalchemy import (
    SQLAlchemyPosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.import_batch.sqlalchemy import (
    SQLAlchemyPosImportBatchRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.sqlalchemy import (
    SQLAlchemyPosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyPosReceiptRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.sqlalchemy import (
    SQLAlchemyPosSourceRepository,
)
from tests.modules.helpers import TEST_PREFIX
from tests.modules.pos.helpers import (
    DOKA_ORG_ID,
    OCCURRED_AT,
    PRODUCT_GUID,
    RECEIPT_GUID,
    build_posting_service,
    receive,
)

pytestmark = pytest.mark.db


def build_receipt(
    *,
    source_id: UUID,
    org_unit_id: UUID,
    product_guid: str,
    quantity: str,
    guid: str = RECEIPT_GUID,
) -> PosReceipt:
    receipt_id = uuid4()
    line = PosReceiptLine.create(
        receipt_id=receipt_id,
        line_number=1,
        external_guid=None,
        product_guid=product_guid,
        product_name=f"{TEST_PREFIX}Медовик",
        unit="кг",
        quantity=Decimal(quantity),
        price_kopecks=25000,
        amount_kopecks=25000,
        raw={"ProductName": f"{TEST_PREFIX}Медовик"},
    )

    return PosReceipt.create(
        receipt_id=receipt_id,
        source_id=source_id,
        agent_id=None,
        batch_id=None,
        external_guid=guid,
        occurred_at=OCCURRED_AT,
        kind="sale",
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
        org_unit_id=org_unit_id,
        lines=[line],
        raw={"guid": guid},
    )


async def build_source(session, org_unit_id: UUID) -> tuple[PosSource, PosAgent]:
    source = PosSource.create(
        doka_org_id=DOKA_ORG_ID,
        name=f"{TEST_PREFIX}Кафе",
        org_unit_id=org_unit_id,
    )
    await SQLAlchemyPosSourceRepository(session).add(source)

    raw_key = generate_api_key()
    agent = PosAgent.create(
        source_id=source.id,
        api_key_hash=hash_api_key(raw_key),
        api_key_prefix=api_key_prefix(raw_key),
        install_id="install-1",
    )
    await SQLAlchemyPosAgentRepository(session).add(agent)
    await session.commit()

    return source, agent


async def test_posting_deducts_stock_and_is_idempotent(
    db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "10", "100")

    source, _ = await build_source(db_session, warehouse.id)
    repository = SQLAlchemyPosReceiptRepository(db_session)
    receipt = build_receipt(
        source_id=source.id,
        org_unit_id=warehouse.id,
        product_guid=PRODUCT_GUID,
        quantity="3",
    )
    receipt.lines[0].map_to(nomenclature.id)
    receipt.refresh_status()
    assert receipt.status is PosReceiptStatus.READY

    await repository.add_if_absent(receipt)
    await db_session.commit()

    service = build_posting_service(db_session, repository)
    posted = await service.post(receipt)
    assert posted.status is PosReceiptStatus.POSTED

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(7)

    # Повторное проведение не списывает товар ещё раз.
    posted = await service.post(posted)
    assert posted.status is PosReceiptStatus.POSTED

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(7)


async def test_shortage_marks_receipt_as_needs_stock(
    db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "2", "100")

    source, _ = await build_source(db_session, warehouse.id)
    repository = SQLAlchemyPosReceiptRepository(db_session)
    receipt = build_receipt(
        source_id=source.id,
        org_unit_id=warehouse.id,
        product_guid=PRODUCT_GUID,
        quantity="5",
    )
    receipt.lines[0].map_to(nomenclature.id)
    receipt.refresh_status()

    await repository.add_if_absent(receipt)
    await db_session.commit()

    service = build_posting_service(db_session, repository)
    posted = await service.post(receipt)

    assert posted.status is PosReceiptStatus.NEEDS_STOCK
    assert posted.error

    stored = await repository.get_by_id(receipt.id)
    assert stored is not None
    assert stored.status is PosReceiptStatus.NEEDS_STOCK

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(2)

    posting_repository = SQLAlchemyStockPostingRepository(db_session)
    assert not await posting_repository.exists(
        document_type=DocumentType.SALE, document_id=receipt.id
    )


async def test_import_is_deduplicated_and_posts_after_mapping(
    db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()
    await receive(db_session, warehouse.id, nomenclature.id, "10", "100")

    source, agent = await build_source(db_session, warehouse.id)
    receipt_repository = SQLAlchemyPosReceiptRepository(db_session)
    product_map_repository = SQLAlchemyPosProductMapRepository(db_session)
    transactions = SQLAlchemyTransactionManager(db_session)

    interactor = ImportPosReceiptsInteractor(
        receipt_repository=receipt_repository,
        import_batch_repository=SQLAlchemyPosImportBatchRepository(db_session),
        product_map_repository=product_map_repository,
        agent_repository=SQLAlchemyPosAgentRepository(db_session),
        posting_service=build_posting_service(db_session, receipt_repository),
        transaction_manager=transactions,
    )

    incoming = IncomingReceipt(
        guid=RECEIPT_GUID,
        occurred_at=OCCURRED_AT,
        kind="sale",
        payment_kind="card",
        total_kopecks=75000,
        subdivision_code="1",
        subdivision_name="Торговый зал",
        cashier="Администратор",
        shift="422",
        number="1",
        fd_number="18747",
        fp_number="1603810978",
        fn_number="7380440902472099",
        lines=(
            IncomingReceiptLine(
                guid=None,
                product_guid=PRODUCT_GUID,
                product_name=f"{TEST_PREFIX}Медовик",
                unit="кг",
                quantity=Decimal(3),
                price_kopecks=25000,
                amount_kopecks=75000,
                discount_kopecks=0,
                barcode=None,
                mark_code=None,
            ),
        ),
        raw={"guid": RECEIPT_GUID},
    )

    command = ImportPosReceiptsCommand(
        source=source,
        agent=agent,
        file_name="Обмен_Продаж_27.10.2026.xml",
        file_sha256="a" * 64,
        exported_at=OCCURRED_AT,
        receipts=(incoming,),
    )

    first = await interactor(command)
    assert [item.status for item in first.results] == ["pending_unmapped"]

    stored = await receipt_repository.get_by_source_guid(source.id, RECEIPT_GUID)
    assert stored is not None
    assert stored.status is PosReceiptStatus.NEEDS_MAPPING

    mapping = PosProductMapping.create(
        source_id=source.id,
        doka_product_guid=PRODUCT_GUID,
        nomenclature_id=nomenclature.id,
        unit_factor=Decimal(1),
    )
    await product_map_repository.upsert(mapping)
    affected = await receipt_repository.apply_mapping(
        source_id=source.id,
        doka_product_guid=PRODUCT_GUID,
        nomenclature_id=nomenclature.id,
        unit_factor=Decimal(1),
    )
    assert affected == [stored.id]

    refreshed = await receipt_repository.get_by_id(stored.id)
    assert refreshed is not None
    refreshed.refresh_status()
    await receipt_repository.save(refreshed)
    await transactions.commit()
    assert refreshed.status is PosReceiptStatus.READY

    # Повторная доставка того же чека — duplicate, но сервер доводит его сам.
    second = await interactor(command)
    assert [item.status for item in second.results] == ["duplicate"]

    stored = await receipt_repository.get_by_id(stored.id)
    assert stored is not None
    assert stored.status is PosReceiptStatus.POSTED

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(7)

    third = await interactor(command)
    assert [item.status for item in third.results] == ["duplicate"]

    balance = await SQLAlchemyStockBalanceRepository(db_session).get(
        warehouse.id, nomenclature.id
    )
    assert balance is not None
    assert balance.quantity == Decimal(7)


async def test_product_mapping_upsert_keeps_one_row_per_product(
    db_session, warehouse, make_nomenclature
) -> None:
    first_nomenclature = await make_nomenclature()
    second_nomenclature = await make_nomenclature()

    source, _ = await build_source(db_session, warehouse.id)
    repository = SQLAlchemyPosProductMapRepository(db_session)

    mapping = PosProductMapping.create(
        source_id=source.id,
        doka_product_guid=PRODUCT_GUID,
        nomenclature_id=first_nomenclature.id,
        unit_factor=Decimal(1),
    )
    mapping_id = await repository.upsert(mapping)

    updated = PosProductMapping.create(
        source_id=source.id,
        doka_product_guid=PRODUCT_GUID.lower(),
        nomenclature_id=second_nomenclature.id,
        unit_factor=Decimal("0.001"),
    )
    assert await repository.upsert(updated) == mapping_id

    stored = await repository.get_by_source_product(source.id, PRODUCT_GUID)
    assert stored is not None
    assert stored.id == mapping_id
    assert stored.nomenclature_id == second_nomenclature.id
    assert stored.unit_factor == Decimal("0.001000")

    mappings = await repository.list_by_source(source.id)
    assert len(mappings) == 1


async def test_unmapped_products_reader_lists_only_unmapped(
    db_session, warehouse, make_nomenclature
) -> None:
    nomenclature = await make_nomenclature()

    source, _ = await build_source(db_session, warehouse.id)
    receipt_repository = SQLAlchemyPosReceiptRepository(db_session)

    unmapped = build_receipt(
        source_id=source.id,
        org_unit_id=warehouse.id,
        product_guid=PRODUCT_GUID,
        quantity="1",
        guid="AA" * 22,
    )
    await receipt_repository.add_if_absent(unmapped)

    mapped = build_receipt(
        source_id=source.id,
        org_unit_id=warehouse.id,
        product_guid="BB" * 22,
        quantity="1",
        guid="CC" * 22,
    )
    mapped.lines[0].map_to(nomenclature.id)
    mapped.refresh_status()
    await receipt_repository.add_if_absent(mapped)
    await db_session.commit()

    items = await SQLAlchemyPosProductMapReader(db_session).unmapped_products(
        source.id
    )

    assert [item.product_guid for item in items] == [PRODUCT_GUID]
