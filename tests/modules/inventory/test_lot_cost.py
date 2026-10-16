from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.interactors.production.post_production import (
    PostProductionCommand,
    ProductionIssueCommand,
    ProductionReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptCommand,
    ReceiptLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.sales.post_sale import (
    PostSaleCommand,
    SaleLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffCommand,
    WriteOffLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
    PostWriteOffCommand,
)
from myasnaya_derevnya.modules.inventory.domain.errors import InsufficientStockError
from myasnaya_derevnya.modules.inventory.infrastructure.readers.lot_balance.sqlalchemy import (
    SQLAlchemyLotBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from tests.modules.inventory.helpers import (
    build_interactors,
    build_production_interactor,
    build_sale_interactor,
)

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


async def receive(
    session: AsyncSession,
    org_unit_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    unit_cost: str,
    lot_code: str | None = None,
    expires_at: date | None = None,
) -> None:
    interactors = build_interactors(session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost),
                    lot_code=lot_code,
                    expires_at=expires_at,
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))


async def write_off(
    session: AsyncSession,
    org_unit_id: UUID,
    nomenclature_id: UUID,
    quantity: str,
    lot_code: str | None = None,
) -> None:
    interactors = build_interactors(session)
    write_off_id = await interactors.create_write_off(
        CreateWriteOffCommand(
            org_unit_id=org_unit_id,
            occurred_at=OCCURRED_AT,
            lines=[
                WriteOffLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    lot_code=lot_code,
                )
            ],
        )
    )
    await interactors.post_write_off(PostWriteOffCommand(write_off_id=write_off_id))


async def balance_of(session: AsyncSession, org_unit_id: UUID, nomenclature_id: UUID):
    return await SQLAlchemyStockBalanceRepository(session).get(
        org_unit_id, nomenclature_id
    )


async def lot_rows(session: AsyncSession, nomenclature_id: UUID) -> dict:
    rows = (
        await session.execute(
            text(
                "select l.lot_code, lb.quantity, lb.total_value"
                " from inventory.stock_lot_balances lb"
                " join inventory.stock_lots l on l.id = lb.lot_id"
                " where lb.nomenclature_id = :nomenclature_id"
            ),
            {"nomenclature_id": nomenclature_id},
        )
    ).all()

    return {row.lot_code: row for row in rows}


async def test_write_off_uses_lot_cost_and_fefo(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()

    await receive(
        db_session, warehouse.id, meat.id, "100", "500", "M-01", date(2026, 10, 10)
    )
    await receive(
        db_session, warehouse.id, meat.id, "100", "600", "M-02", date(2026, 10, 20)
    )

    await write_off(db_session, warehouse.id, meat.id, "30")

    balance = await balance_of(db_session, warehouse.id, meat.id)
    lots = await lot_rows(db_session, meat.id)

    assert balance.quantity == Decimal(170)
    assert balance.total_value.kopecks == 9_500_000
    assert lots["M-01"].quantity == Decimal(70)
    assert lots["M-01"].total_value == 3_500_000
    assert lots["M-02"].quantity == Decimal(100)
    assert lots["M-02"].total_value == 6_000_000


async def test_write_off_splits_across_lots_by_fefo(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()

    await receive(
        db_session, warehouse.id, meat.id, "100", "500", "M-01", date(2026, 10, 10)
    )
    await receive(
        db_session, warehouse.id, meat.id, "100", "600", "M-02", date(2026, 10, 20)
    )

    await write_off(db_session, warehouse.id, meat.id, "150")

    balance = await balance_of(db_session, warehouse.id, meat.id)
    lots = await lot_rows(db_session, meat.id)

    assert balance.quantity == Decimal(50)
    assert balance.total_value.kopecks == 3_000_000
    assert lots["M-01"].quantity == Decimal(0)
    assert lots["M-01"].total_value == 0
    assert lots["M-02"].quantity == Decimal(50)
    assert lots["M-02"].total_value == 3_000_000


async def test_non_lot_stock_uses_average_cost(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    packaging = await make_nomenclature()

    await receive(db_session, warehouse.id, packaging.id, "10", "100")
    await write_off(db_session, warehouse.id, packaging.id, "4")

    balance = await balance_of(db_session, warehouse.id, packaging.id)
    lots = await lot_rows(db_session, packaging.id)

    assert balance.quantity == Decimal(6)
    assert balance.total_value.kopecks == 60_000
    assert lots == {}


async def test_production_transfers_lot_cost_to_output(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()
    sausage = await make_nomenclature()

    await receive(
        db_session, warehouse.id, meat.id, "100", "500", "M-01", date(2026, 10, 10)
    )
    await receive(
        db_session, warehouse.id, meat.id, "100", "600", "M-02", date(2026, 10, 20)
    )

    interactor = build_production_interactor(db_session)
    posted = await interactor(
        PostProductionCommand(
            document_id=uuid4(),
            org_unit_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            issues=(
                ProductionIssueCommand(
                    nomenclature_id=meat.id, quantity=Decimal(100)
                ),
            ),
            receipts=(
                ProductionReceiptCommand(
                    nomenclature_id=sausage.id,
                    quantity=Decimal(100),
                    share=Decimal(1),
                    lot_code="K-01",
                    expires_at=date(2026, 10, 15),
                ),
            ),
        )
    )

    balance = await balance_of(db_session, warehouse.id, sausage.id)
    lots = await lot_rows(db_session, sausage.id)

    assert posted.issued_cost_kopecks == 5_000_000
    assert posted.receipts[0].cost_kopecks == 5_000_000
    assert balance.total_value.kopecks == 5_000_000
    assert lots["K-01"].total_value == 5_000_000


async def test_sale_writes_off_by_fefo_and_returns_cost(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    sausage = await make_nomenclature()

    await receive(
        db_session,
        warehouse.id,
        sausage.id,
        "100",
        "500",
        "K-01",
        date(2026, 10, 10),
    )
    await receive(
        db_session,
        warehouse.id,
        sausage.id,
        "100",
        "600",
        "K-02",
        date(2026, 10, 20),
    )

    interactor = build_sale_interactor(db_session)
    posted = await interactor(
        PostSaleCommand(
            document_id=uuid4(),
            org_unit_id=warehouse.id,
            occurred_at=OCCURRED_AT,
            lines=(
                SaleLineCommand(
                    nomenclature_id=sausage.id, quantity=Decimal(150)
                ),
            ),
        )
    )

    balance = await balance_of(db_session, warehouse.id, sausage.id)
    lots = await lot_rows(db_session, sausage.id)

    assert posted.line_costs_kopecks == (8_000_000,)
    assert balance.quantity == Decimal(50)
    assert balance.total_value.kopecks == 3_000_000
    assert lots["K-01"].quantity == Decimal(0)
    assert lots["K-02"].quantity == Decimal(50)


async def test_sale_without_enough_stock_is_rejected(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    sausage = await make_nomenclature()

    await receive(db_session, warehouse.id, sausage.id, "10", "500", "K-01")

    interactor = build_sale_interactor(db_session)

    with pytest.raises(InsufficientStockError):
        await interactor(
            PostSaleCommand(
                document_id=uuid4(),
                org_unit_id=warehouse.id,
                occurred_at=OCCURRED_AT,
                lines=(
                    SaleLineCommand(
                        nomenclature_id=sausage.id, quantity=Decimal(20)
                    ),
                ),
            )
        )


async def test_lot_reader_orders_by_expiry_and_filters(
    db_session: AsyncSession, make_location, make_nomenclature
) -> None:
    warehouse = await make_location()
    meat = await make_nomenclature()

    await receive(
        db_session, warehouse.id, meat.id, "10", "100", "M-20", date(2026, 10, 20)
    )
    await receive(
        db_session, warehouse.id, meat.id, "10", "100", "M-10", date(2026, 10, 10)
    )
    await receive(db_session, warehouse.id, meat.id, "10", "100")

    reader = SQLAlchemyLotBalanceReader(db_session)

    items = await reader.list_by_org_unit(warehouse.id, with_cost=True)
    assert [item.lot_code for item in items] == ["M-10", "M-20"]
    assert all(item.unit_cost is not None for item in items)
    assert all(item.total_value_kopecks is not None for item in items)

    expiring = await reader.list_by_org_unit(
        warehouse.id, with_cost=True, expiring_before=date(2026, 10, 15)
    )
    assert [item.lot_code for item in expiring] == ["M-10"]

    hidden_cost = await reader.list_by_org_unit(warehouse.id, with_cost=False)
    assert all(item.unit_cost is None for item in hidden_cost)
    assert all(item.total_value_kopecks is None for item in hidden_cost)
