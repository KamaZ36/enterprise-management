from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    AmbiguousLotCodeError,
    LotVetisConflictError,
    StockLotNotFoundError,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.sqlalchemy import (
    SQLAlchemyStockLotRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_LOTS_TABLE,
)
from tests.modules.inventory.helpers import build_interactors

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


async def receive(
    session: AsyncSession,
    org_unit_id: UUID,
    nomenclature_id: UUID,
    *,
    lot_code: str,
    supplier_name: str | None,
    quantity: str = "10",
    vetis_vsd_number: str | None = None,
    vetis_vsd_guid: UUID | None = None,
    vetis_batch_id: str | None = None,
) -> None:
    interactors = build_interactors(session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            supplier_name=supplier_name,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(100),
                    lot_code=lot_code,
                    vetis_vsd_number=vetis_vsd_number,
                    vetis_vsd_guid=vetis_vsd_guid,
                    vetis_batch_id=vetis_batch_id,
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))


async def lot_codes(
    session: AsyncSession, nomenclature_id: UUID
) -> list[str]:
    rows = (
        await session.execute(
            select(STOCK_LOTS_TABLE.c.lot_code).where(
                STOCK_LOTS_TABLE.c.nomenclature_id == nomenclature_id
            )
        )
    ).all()

    return [row.lot_code for row in rows]


async def test_same_code_from_different_suppliers_creates_two_lots(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-01",
        supplier_name="Ферма Ивановых",
    )
    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-01",
        supplier_name="Мясокомбинат",
    )

    assert await lot_codes(db_session, meat.id) == ["M-01", "M-01"]


async def test_same_identity_reuses_lot(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-01",
        supplier_name="Ферма Ивановых",
        quantity="10",
    )
    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-01",
        supplier_name="Ферма Ивановых",
        quantity="5",
    )

    assert await lot_codes(db_session, meat.id) == ["M-01"]


async def test_require_rejects_ambiguous_lot_code(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-01",
        supplier_name="Ферма Ивановых",
    )
    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-01",
        supplier_name="Мясокомбинат",
    )

    resolver = LotResolver(SQLAlchemyStockLotRepository(db_session))

    with pytest.raises(AmbiguousLotCodeError):
        await resolver.require(nomenclature_id=meat.id, lot_code="M-01")


async def test_require_reports_unknown_code(
    db_session: AsyncSession, make_nomenclature
) -> None:
    meat = await make_nomenclature()
    resolver = LotResolver(SQLAlchemyStockLotRepository(db_session))

    with pytest.raises(StockLotNotFoundError):
        await resolver.require(nomenclature_id=meat.id, lot_code="M-404")


async def test_receipt_copies_vetis_to_lot(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()
    vsd_guid = uuid4()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-VSD",
        supplier_name="Ферма Ивановых",
        vetis_vsd_number="ВСД-123",
        vetis_vsd_guid=vsd_guid,
        vetis_batch_id="BATCH-1",
    )

    repository = SQLAlchemyStockLotRepository(db_session)
    lot = await repository.get_by_identity(
        nomenclature_id=meat.id,
        lot_code="M-VSD",
        produced_at=None,
        supplier_name="Ферма Ивановых",
    )

    assert lot is not None
    assert lot.vetis_vsd_number == "ВСД-123"
    assert lot.vetis_vsd_guid == vsd_guid
    assert lot.vetis_batch_id == "BATCH-1"
    assert lot.vetis_entered_at is not None


async def test_receipt_without_vetis_keeps_existing_lot_vetis(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()
    vsd_guid = uuid4()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-VSD",
        supplier_name="Ферма Ивановых",
        vetis_vsd_number="ВСД-123",
        vetis_vsd_guid=vsd_guid,
    )
    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-VSD",
        supplier_name="Ферма Ивановых",
        quantity="5",
    )

    repository = SQLAlchemyStockLotRepository(db_session)
    lot = await repository.get_by_identity(
        nomenclature_id=meat.id,
        lot_code="M-VSD",
        produced_at=None,
        supplier_name="Ферма Ивановых",
    )

    assert lot is not None
    assert lot.vetis_vsd_guid == vsd_guid


async def test_second_vsd_for_same_lot_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()
    first_guid = uuid4()
    second_guid = uuid4()

    await receive(
        db_session,
        warehouse.id,
        meat.id,
        lot_code="M-VSD",
        supplier_name="Ферма Ивановых",
        vetis_vsd_number="ВСД-123",
        vetis_vsd_guid=first_guid,
    )

    with pytest.raises(LotVetisConflictError):
        await receive(
            db_session,
            warehouse.id,
            meat.id,
            lot_code="M-VSD",
            supplier_name="Ферма Ивановых",
            vetis_vsd_number="ВСД-456",
            vetis_vsd_guid=second_guid,
        )
