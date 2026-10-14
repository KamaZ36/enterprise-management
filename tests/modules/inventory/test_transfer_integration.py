from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
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
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.create import (
    CreateTransferCommand,
    CreateTransferInteractor,
    TransferLineCommand,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.post import (
    PostTransferCommand,
    PostTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
from myasnaya_derevnya.modules.inventory.application.services.posting_preconditions import (
    PostingPreconditions,
)
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.application.services.transfer_posting import (
    TransferPosting,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InsufficientStockError,
)
from myasnaya_derevnya.modules.inventory.domain.services.cost_policy import (
    MovingAverageCostPolicy,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.sqlalchemy import (
    SQLAlchemyStockLotRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.sqlalchemy import (
    SQLAlchemyStockLotBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.sqlalchemy import (
    SQLAlchemyStockMovementRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.sqlalchemy import (
    SQLAlchemyStockPostingRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.sqlalchemy import (
    SQLAlchemyTransferRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.sqlalchemy import (
    SQLAlchemyWarehouseRepository,
)
from tests.modules.inventory.helpers import (
    FakeIdentityProvider,
    FakeStaffAPI,
    build_interactors,
)

pytestmark = pytest.mark.db

OCCURRED_AT = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def build_transfer_interactors(session: AsyncSession):
    identity = FakeIdentityProvider(uuid4())
    staff_api = FakeStaffAPI()
    transaction_manager = SQLAlchemyTransactionManager(session)

    warehouses = SQLAlchemyWarehouseRepository(session)
    transfers = SQLAlchemyTransferRepository(session)
    lots = SQLAlchemyStockLotRepository(session)

    preconditions = PostingPreconditions(
        warehouse_repository=warehouses,
        catalog_api=CatalogAPI(
            get_point_prices_interactor=GetPointPricesInteractor(
                binding_repository=SQLAlchemyPriceListBindingRepository(session),
                price_repository=SQLAlchemyPriceRepository(session),
            ),
            nomenclature_repository=SQLAlchemyNomenclatureRepository(session),
        ),
    )
    ledger = StockLedger(
        posting_repository=SQLAlchemyStockPostingRepository(session),
        movement_repository=SQLAlchemyStockMovementRepository(session),
        balance_repository=SQLAlchemyStockBalanceRepository(session),
        lot_balance_repository=SQLAlchemyStockLotBalanceRepository(session),
        cost_policy=MovingAverageCostPolicy(),
    )
    transfer_posting = TransferPosting(
        ledger=ledger, lot_resolver=LotResolver(lot_repository=lots)
    )

    return (
        CreateTransferInteractor(
            identity_provider=identity,
            warehouse_repository=warehouses,
            transfer_repository=transfers,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
        PostTransferInteractor(
            identity_provider=identity,
            transfer_repository=transfers,
            staff_api=staff_api,
            preconditions=preconditions,
            transfer_posting=transfer_posting,
            transaction_manager=transaction_manager,
        ),
        SQLAlchemyStockBalanceRepository(session),
    )


async def receive(
    db_session: AsyncSession,
    warehouse_id,
    nomenclature_id,
    quantity: str,
    unit_cost: str,
    lot_code: str | None = None,
) -> None:
    interactors = build_interactors(db_session)
    receipt_id = await interactors.create_receipt(
        CreateReceiptCommand(
            warehouse_id=warehouse_id,
            occurred_at=OCCURRED_AT,
            supplier_name="Мясокомбинат",
            lines=[
                ReceiptLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    unit_cost=Decimal(unit_cost),
                    lot_code=lot_code,
                )
            ],
        )
    )
    await interactors.post_receipt(PostReceiptCommand(receipt_id=receipt_id))


async def transfer(
    db_session: AsyncSession,
    from_warehouse_id,
    to_warehouse_id,
    nomenclature_id,
    quantity: str,
    lot_code: str | None = None,
) -> None:
    create, post, _ = build_transfer_interactors(db_session)
    transfer_id = await create(
        CreateTransferCommand(
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            occurred_at=OCCURRED_AT,
            lines=[
                TransferLineCommand(
                    nomenclature_id=nomenclature_id,
                    quantity=Decimal(quantity),
                    lot_code=lot_code,
                )
            ],
        )
    )
    await post(PostTransferCommand(transfer_id=transfer_id))


async def test_transfer_moves_quantity_and_keeps_unit_cost(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    source = await make_warehouse()
    target = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, source.id, nomenclature.id, "10", "450", lot_code="LOT-1")
    await transfer(
        db_session, source.id, target.id, nomenclature.id, "4", lot_code="LOT-1"
    )

    _, _, balances = build_transfer_interactors(db_session)
    source_balance = await balances.get(source.id, nomenclature.id)
    target_balance = await balances.get(target.id, nomenclature.id)

    assert source_balance is not None
    assert target_balance is not None
    assert source_balance.quantity == Decimal(6)
    assert target_balance.quantity == Decimal(4)
    assert source_balance.average_unit_cost == Decimal(450)
    assert target_balance.average_unit_cost == Decimal(450)


async def test_transfer_moves_lot_between_warehouses(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    source = await make_warehouse()
    target = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, source.id, nomenclature.id, "10", "450", lot_code="LOT-2")
    await transfer(
        db_session, source.id, target.id, nomenclature.id, "4", lot_code="LOT-2"
    )

    rows = (
        await db_session.execute(
            text(
                "select warehouse_id, quantity from inventory.stock_lot_balances"
                " where nomenclature_id = :nomenclature_id"
            ),
            {"nomenclature_id": nomenclature.id},
        )
    ).all()

    quantities = {row.warehouse_id: row.quantity for row in rows}

    assert quantities[source.id] == Decimal(6)
    assert quantities[target.id] == Decimal(4)


async def test_transfer_more_than_available_is_rejected(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    source = await make_warehouse()
    target = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, source.id, nomenclature.id, "3", "450", lot_code="LOT-3")

    with pytest.raises(InsufficientStockError):
        await transfer(db_session, source.id, target.id, nomenclature.id, "5")

    _, _, balances = build_transfer_interactors(db_session)
    source_balance = await balances.get(source.id, nomenclature.id)
    target_balance = await balances.get(target.id, nomenclature.id)

    assert source_balance is not None
    assert source_balance.quantity == Decimal(3)
    assert target_balance is None or target_balance.quantity == Decimal(0)


async def test_transfer_cannot_be_posted_twice(
    db_session: AsyncSession, make_warehouse, make_nomenclature
) -> None:
    source = await make_warehouse()
    target = await make_warehouse()
    nomenclature = await make_nomenclature()

    await receive(db_session, source.id, nomenclature.id, "5", "450", lot_code="LOT-4")

    create, post, _ = build_transfer_interactors(db_session)
    transfer_id = await create(
        CreateTransferCommand(
            from_warehouse_id=source.id,
            to_warehouse_id=target.id,
            occurred_at=OCCURRED_AT,
            lines=[
                TransferLineCommand(
                    nomenclature_id=nomenclature.id, quantity=Decimal(1)
                )
            ],
        )
    )

    await post(PostTransferCommand(transfer_id=transfer_id))

    with pytest.raises(DocumentAlreadyPostedError):
        await post(PostTransferCommand(transfer_id=transfer_id))
