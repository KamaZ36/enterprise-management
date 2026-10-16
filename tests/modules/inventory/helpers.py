from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

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
from myasnaya_derevnya.modules.inventory.application.interactors.production.post_production import (
    PostProductionInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.sales.post_sale import (
    PostSaleInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
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
from myasnaya_derevnya.modules.inventory.infrastructure.readers.warehouse.sqlalchemy import (
    SQLAlchemyWarehouseReader,
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
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)


class FakeIdentityProvider:
    def __init__(self, user_id: UUID) -> None:
        self._user_id = user_id

    async def get_current_user_id(self) -> UUID:
        return self._user_id

    async def get_current_session_id(self) -> UUID:
        return self._user_id


class FakeBusinessAPI:
    def __init__(self, root_unit_id: UUID) -> None:
        self._root_unit_id = root_unit_id

    async def get_root_unit_id(self) -> UUID:
        return self._root_unit_id


class FakeStaffAPI:
    def __init__(
        self,
        allowed: bool = True,
        scope: AccessScope | None = None,
    ) -> None:
        self.allowed = allowed
        self.scope = scope if scope is not None else AccessScope.company_wide()
        self.checked: list[tuple[str, UUID | None]] = []
        self.scope_checked: list[str] = []

    async def can(
        self, user_id: UUID, permission: Any, org_unit_id: UUID | None
    ) -> bool:
        self.checked.append((permission.code, org_unit_id))
        return self.allowed

    async def scope_for(self, user_id: UUID, permission: Any) -> AccessScope:
        self.scope_checked.append(permission.code)
        return self.scope


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
    identity = FakeIdentityProvider(uuid4())
    staff_api = FakeStaffAPI(allowed=allowed)
    transaction_manager = SQLAlchemyTransactionManager(session)

    warehouses = SQLAlchemyWarehouseRepository(session)
    receipts = SQLAlchemyReceiptRepository(session)
    write_offs = SQLAlchemyWriteOffRepository(session)

    preconditions, lot_resolver, ledger = build_posting(session)

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


def build_posting(
    session: AsyncSession,
) -> tuple[PostingPreconditions, LotResolver, StockLedger]:
    warehouses = SQLAlchemyWarehouseRepository(session)
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
    lot_resolver = LotResolver(lot_repository=lots)
    ledger = StockLedger(
        posting_repository=SQLAlchemyStockPostingRepository(session),
        movement_repository=SQLAlchemyStockMovementRepository(session),
        balance_repository=SQLAlchemyStockBalanceRepository(session),
        lot_balance_repository=SQLAlchemyStockLotBalanceRepository(session),
        cost_policy=MovingAverageCostPolicy(),
    )

    return preconditions, lot_resolver, ledger


def build_production_interactor(session: AsyncSession) -> PostProductionInteractor:
    preconditions, lot_resolver, ledger = build_posting(session)

    return PostProductionInteractor(
        preconditions=preconditions,
        lot_resolver=lot_resolver,
        ledger=ledger,
    )


def build_sale_interactor(session: AsyncSession) -> PostSaleInteractor:
    preconditions, _lot_resolver, ledger = build_posting(session)

    return PostSaleInteractor(preconditions=preconditions, ledger=ledger)


def build_inventory_api(session: AsyncSession) -> InventoryAPI:
    interactors = build_interactors(session)

    return InventoryAPI(
        create_receipt_interactor=interactors.create_receipt,
        post_receipt_interactor=interactors.post_receipt,
        post_production_interactor=build_production_interactor(session),
        post_sale_interactor=build_sale_interactor(session),
        balance_repository=SQLAlchemyStockBalanceRepository(session),
        warehouse_repository=SQLAlchemyWarehouseRepository(session),
        warehouse_reader=SQLAlchemyWarehouseReader(session),
    )


async def movement_totals(
    session: AsyncSession, warehouse_id: UUID, nomenclature_id: UUID
) -> tuple[Decimal, int]:
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
