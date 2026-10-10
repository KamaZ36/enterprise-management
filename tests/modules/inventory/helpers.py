"""Вспомогательные объекты тестов: настоящие репозитории, заглушки для прав."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.sqlalchemy import (
    SQLAlchemyTransactionManager,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.sqlalchemy import (
    SQLAlchemyNomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.interactors.create_receipt import (
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_write_off import (
    CreateWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_receipt import (
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_write_off import (
    PostWriteOffInteractor,
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
from myasnaya_derevnya.modules.inventory.domain.services.cost_policy import (
    MovingAverageCostPolicy,
)
from myasnaya_derevnya.modules.inventory.domain.services.warehouse_purpose import (
    WarehousePurposePolicy,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyReceiptRepository,
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
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.sqlalchemy import (
    SQLAlchemyWarehouseRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.sqlalchemy import (
    SQLAlchemyWriteOffRepository,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id

    async def get_current_session_id(self) -> UUID:
        return self._user_id


class FakeStaffAPI:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.checked: list[tuple[str, UUID | None]] = []

    async def can(
        self, user_id: UUID, permission: Any, org_unit_id: UUID | None
    ) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed


@dataclass(frozen=True, slots=True)
class InventoryInteractors:
    create_receipt: CreateReceiptInteractor
    post_receipt: PostReceiptInteractor
    create_write_off: CreateWriteOffInteractor
    post_write_off: PostWriteOffInteractor
    staff_api: FakeStaffAPI


def build_interactors(
    session: AsyncSession, *, allowed: bool = True
) -> InventoryInteractors:
    """Собирает граф модуля вручную: настоящие репозитории, заглушки прав."""
    identity = FakeIdentityProvider(uuid4())
    staff_api = FakeStaffAPI(allowed=allowed)
    transaction_manager = SQLAlchemyTransactionManager(session)

    warehouses = SQLAlchemyWarehouseRepository(session)
    receipts = SQLAlchemyReceiptRepository(session)
    write_offs = SQLAlchemyWriteOffRepository(session)
    lots = SQLAlchemyStockLotRepository(session)

    preconditions = PostingPreconditions(
        warehouse_repository=warehouses,
        catalog_api=CatalogAPI(SQLAlchemyNomenclatureRepository(session)),
        purpose_policy=WarehousePurposePolicy(),
    )
    lot_resolver = LotResolver(lot_repository=lots)
    ledger = StockLedger(
        posting_repository=SQLAlchemyStockPostingRepository(session),
        movement_repository=SQLAlchemyStockMovementRepository(session),
        balance_repository=SQLAlchemyStockBalanceRepository(session),
        lot_balance_repository=SQLAlchemyStockLotBalanceRepository(session),
        cost_policy=MovingAverageCostPolicy(),
    )

    return InventoryInteractors(
        create_receipt=CreateReceiptInteractor(
            identity_provider=identity,
            warehouse_repository=warehouses,
            receipt_repository=receipts,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
        post_receipt=PostReceiptInteractor(
            identity_provider=identity,
            receipt_repository=receipts,
            staff_api=staff_api,
            preconditions=preconditions,
            lot_resolver=lot_resolver,
            ledger=ledger,
            transaction_manager=transaction_manager,
        ),
        create_write_off=CreateWriteOffInteractor(
            identity_provider=identity,
            warehouse_repository=warehouses,
            write_off_repository=write_offs,
            staff_api=staff_api,
            transaction_manager=transaction_manager,
        ),
        post_write_off=PostWriteOffInteractor(
            identity_provider=identity,
            write_off_repository=write_offs,
            warehouse_repository=warehouses,
            staff_api=staff_api,
            preconditions=preconditions,
            lot_resolver=lot_resolver,
            ledger=ledger,
            transaction_manager=transaction_manager,
        ),
        staff_api=staff_api,
    )


async def movement_totals(
    session: AsyncSession, warehouse_id: UUID, nomenclature_id: UUID
) -> tuple[Decimal, int]:
    """Сумма проводок — эталон, с которым сверяется баланс."""
    row = (
        await session.execute(
            text(
                "select coalesce(sum(quantity), 0) as quantity,"
                " coalesce(sum(total_cost), 0) as total_cost"
                " from inventory.stock_movements"
                " where warehouse_id = :warehouse_id"
                " and nomenclature_id = :nomenclature_id"
            ),
            {"warehouse_id": warehouse_id, "nomenclature_id": nomenclature_id},
        )
    ).one()

    return row.quantity, row.total_cost
