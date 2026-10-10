from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.interactors.create_receipt import (
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_warehouse import (
    CreateWarehouseInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.create_write_off import (
    CreateWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.list_warehouses import (
    ListWarehousesInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_receipt import (
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.post_write_off import (
    PostWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.read_balances import (
    GetBalanceInteractor,
    ListBalancesInteractor,
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
    CostPolicy,
    MovingAverageCostPolicy,
)
from myasnaya_derevnya.modules.inventory.domain.services.warehouse_purpose import (
    WarehousePurposePolicy,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.base import (
    ReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.sqlalchemy import (
    SQLAlchemyStockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.base import (
    StockLotRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.sqlalchemy import (
    SQLAlchemyStockLotRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.base import (
    StockLotBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.sqlalchemy import (
    SQLAlchemyStockLotBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.sqlalchemy import (
    SQLAlchemyStockMovementRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.base import (
    StockPostingRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.sqlalchemy import (
    SQLAlchemyStockPostingRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.base import (
    WarehouseRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.warehouse.sqlalchemy import (
    SQLAlchemyWarehouseRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.sqlalchemy import (
    SQLAlchemyWriteOffRepository,
)
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import InventoryAPI


class InventoryDepProvider(Provider):
    # REPOSITORIES

    @provide(scope=Scope.REQUEST)
    def get_warehouse_repository(self, session: AsyncSession) -> WarehouseRepository:
        return SQLAlchemyWarehouseRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stock_lot_repository(self, session: AsyncSession) -> StockLotRepository:
        return SQLAlchemyStockLotRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stock_posting_repository(
        self, session: AsyncSession
    ) -> StockPostingRepository:
        return SQLAlchemyStockPostingRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_receipt_repository(self, session: AsyncSession) -> ReceiptRepository:
        return SQLAlchemyReceiptRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_write_off_repository(self, session: AsyncSession) -> WriteOffRepository:
        return SQLAlchemyWriteOffRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stock_movement_repository(
        self, session: AsyncSession
    ) -> StockMovementRepository:
        return SQLAlchemyStockMovementRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stock_balance_repository(
        self, session: AsyncSession
    ) -> StockBalanceRepository:
        return SQLAlchemyStockBalanceRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_stock_lot_balance_repository(
        self, session: AsyncSession
    ) -> StockLotBalanceRepository:
        return SQLAlchemyStockLotBalanceRepository(session)

    # DOMAIN SERVICES

    @provide(scope=Scope.REQUEST)
    def get_cost_policy(self) -> CostPolicy:
        return MovingAverageCostPolicy()

    purpose_policy = provide(WarehousePurposePolicy, scope=Scope.REQUEST)

    # APPLICATION SERVICES

    @provide(scope=Scope.REQUEST)
    def get_lot_resolver(self, lot_repository: StockLotRepository) -> LotResolver:
        return LotResolver(lot_repository=lot_repository)

    @provide(scope=Scope.REQUEST)
    def get_posting_preconditions(
        self,
        warehouse_repository: WarehouseRepository,
        catalog_api: CatalogAPI,
        purpose_policy: WarehousePurposePolicy,
    ) -> PostingPreconditions:
        return PostingPreconditions(
            warehouse_repository=warehouse_repository,
            catalog_api=catalog_api,
            purpose_policy=purpose_policy,
        )

    @provide(scope=Scope.REQUEST)
    def get_stock_ledger(
        self,
        posting_repository: StockPostingRepository,
        movement_repository: StockMovementRepository,
        balance_repository: StockBalanceRepository,
        lot_balance_repository: StockLotBalanceRepository,
        cost_policy: CostPolicy,
    ) -> StockLedger:
        return StockLedger(
            posting_repository=posting_repository,
            movement_repository=movement_repository,
            balance_repository=balance_repository,
            lot_balance_repository=lot_balance_repository,
            cost_policy=cost_policy,
        )

    # INTERACTORS

    create_warehouse_interactor = provide(
        CreateWarehouseInteractor, scope=Scope.REQUEST
    )
    list_warehouses_interactor = provide(ListWarehousesInteractor, scope=Scope.REQUEST)
    create_receipt_interactor = provide(CreateReceiptInteractor, scope=Scope.REQUEST)
    post_receipt_interactor = provide(PostReceiptInteractor, scope=Scope.REQUEST)
    create_write_off_interactor = provide(CreateWriteOffInteractor, scope=Scope.REQUEST)
    post_write_off_interactor = provide(PostWriteOffInteractor, scope=Scope.REQUEST)
    get_balance_interactor = provide(GetBalanceInteractor, scope=Scope.REQUEST)
    list_balances_interactor = provide(ListBalancesInteractor, scope=Scope.REQUEST)

    # FACADE

    @provide(scope=Scope.REQUEST)
    def get_inventory_api(
        self,
        create_receipt_interactor: CreateReceiptInteractor,
        post_receipt_interactor: PostReceiptInteractor,
        balance_repository: StockBalanceRepository,
    ) -> InventoryAPI:
        return InventoryAPI(
            create_receipt_interactor=create_receipt_interactor,
            post_receipt_interactor=post_receipt_interactor,
            balance_repository=balance_repository,
        )
