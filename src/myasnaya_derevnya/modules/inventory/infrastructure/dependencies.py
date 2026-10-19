from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.inventory.application.interactors.balances.get import (
    GetBalanceInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.balances.list import (
    ListBalancesInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.create import (
    CreateInventoryCountInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.get import (
    GetInventoryCountInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.list import (
    ListInventoryCountsInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.post import (
    PostInventoryCountInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.inventory_counts.update import (
    UpdateInventoryCountInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.locations.list import (
    ListLocationsInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.lots.list import (
    ListLotBalancesInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.movements.list import (
    ListMovementsInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.production.post_production import (
    PostProductionInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.create import (
    CreateReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.get import (
    GetReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.list import (
    ListReceiptsInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.receipts.post import (
    PostReceiptInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.sales.post_sale import (
    PostSaleInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.create import (
    CreateTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.get import (
    GetTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.list import (
    ListTransfersInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.post import (
    PostTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.transfers.update import (
    UpdateTransferInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.create import (
    CreateWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.get import (
    GetWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.list import (
    ListWriteOffsInteractor,
)
from myasnaya_derevnya.modules.inventory.application.interactors.write_offs.post import (
    PostWriteOffInteractor,
)
from myasnaya_derevnya.modules.inventory.application.services.document_scope import (
    DocumentScope,
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
from myasnaya_derevnya.modules.inventory.domain.services.cost_policy import (
    CostPolicy,
    MovingAverageCostPolicy,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.balance.base import (
    BalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.balance.sqlalchemy import (
    SQLAlchemyBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.inventory_count.base import (
    InventoryCountReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.inventory_count.sqlalchemy import (
    SQLAlchemyInventoryCountReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.lot_balance.base import (
    LotBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.lot_balance.sqlalchemy import (
    SQLAlchemyLotBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.movement.base import (
    MovementReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.movement.sqlalchemy import (
    SQLAlchemyMovementReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.base import (
    ReceiptReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.sqlalchemy import (
    SQLAlchemyReceiptReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.transfer.base import (
    TransferReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.transfer.sqlalchemy import (
    SQLAlchemyTransferReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.base import (
    WriteOffReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.sqlalchemy import (
    SQLAlchemyWriteOffReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.base import (
    InventoryCountRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.sqlalchemy import (
    SQLAlchemyInventoryCountRepository,
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
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.sqlalchemy import (
    SQLAlchemyTransferRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.sqlalchemy import (
    SQLAlchemyWriteOffRepository,
)
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import InventoryAPI


class InventoryDepProvider(Provider):
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
    def get_inventory_count_repository(
        self, session: AsyncSession
    ) -> InventoryCountRepository:
        return SQLAlchemyInventoryCountRepository(session)

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


    @provide(scope=Scope.REQUEST)
    def get_balance_reader(self, session: AsyncSession) -> BalanceReader:
        return SQLAlchemyBalanceReader(session)

    @provide(scope=Scope.REQUEST)
    def get_lot_balance_reader(self, session: AsyncSession) -> LotBalanceReader:
        return SQLAlchemyLotBalanceReader(session)

    @provide(scope=Scope.REQUEST)
    def get_movement_reader(self, session: AsyncSession) -> MovementReader:
        return SQLAlchemyMovementReader(session)

    @provide(scope=Scope.REQUEST)
    def get_receipt_reader(self, session: AsyncSession) -> ReceiptReader:
        return SQLAlchemyReceiptReader(session)

    @provide(scope=Scope.REQUEST)
    def get_write_off_reader(self, session: AsyncSession) -> WriteOffReader:
        return SQLAlchemyWriteOffReader(session)

    @provide(scope=Scope.REQUEST)
    def get_inventory_count_reader(
        self, session: AsyncSession
    ) -> InventoryCountReader:
        return SQLAlchemyInventoryCountReader(session)


    @provide(scope=Scope.REQUEST)
    def get_cost_policy(self) -> CostPolicy:
        return MovingAverageCostPolicy()


    document_scope = provide(DocumentScope, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def get_lot_resolver(self, lot_repository: StockLotRepository) -> LotResolver:
        return LotResolver(lot_repository=lot_repository)

    @provide(scope=Scope.REQUEST)
    def get_posting_preconditions(
        self,
        business_api: BusinessAPI,
        catalog_api: CatalogAPI,
    ) -> PostingPreconditions:
        return PostingPreconditions(
            business_api=business_api,
            catalog_api=catalog_api,
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


    create_receipt_interactor = provide(CreateReceiptInteractor, scope=Scope.REQUEST)
    post_receipt_interactor = provide(PostReceiptInteractor, scope=Scope.REQUEST)
    post_production_interactor = provide(
        PostProductionInteractor, scope=Scope.REQUEST
    )
    post_sale_interactor = provide(PostSaleInteractor, scope=Scope.REQUEST)
    create_write_off_interactor = provide(CreateWriteOffInteractor, scope=Scope.REQUEST)
    post_write_off_interactor = provide(PostWriteOffInteractor, scope=Scope.REQUEST)
    create_inventory_count_interactor = provide(
        CreateInventoryCountInteractor, scope=Scope.REQUEST
    )
    post_inventory_count_interactor = provide(
        PostInventoryCountInteractor, scope=Scope.REQUEST
    )
    list_inventory_counts_interactor = provide(
        ListInventoryCountsInteractor, scope=Scope.REQUEST
    )
    get_inventory_count_interactor = provide(
        GetInventoryCountInteractor, scope=Scope.REQUEST
    )
    update_inventory_count_interactor = provide(
        UpdateInventoryCountInteractor, scope=Scope.REQUEST
    )
    get_balance_interactor = provide(GetBalanceInteractor, scope=Scope.REQUEST)
    list_balances_interactor = provide(ListBalancesInteractor, scope=Scope.REQUEST)
    list_locations_interactor = provide(ListLocationsInteractor, scope=Scope.REQUEST)
    list_movements_interactor = provide(ListMovementsInteractor, scope=Scope.REQUEST)
    list_lot_balances_interactor = provide(
        ListLotBalancesInteractor, scope=Scope.REQUEST
    )
    list_receipts_interactor = provide(ListReceiptsInteractor, scope=Scope.REQUEST)
    get_receipt_interactor = provide(GetReceiptInteractor, scope=Scope.REQUEST)
    list_write_offs_interactor = provide(ListWriteOffsInteractor, scope=Scope.REQUEST)
    get_write_off_interactor = provide(GetWriteOffInteractor, scope=Scope.REQUEST)
    create_transfer_interactor = provide(CreateTransferInteractor, scope=Scope.REQUEST)
    post_transfer_interactor = provide(PostTransferInteractor, scope=Scope.REQUEST)
    list_transfers_interactor = provide(ListTransfersInteractor, scope=Scope.REQUEST)
    get_transfer_interactor = provide(GetTransferInteractor, scope=Scope.REQUEST)
    update_transfer_interactor = provide(UpdateTransferInteractor, scope=Scope.REQUEST)


    @provide(scope=Scope.REQUEST)
    def get_transfer_reader(self, session: AsyncSession) -> TransferReader:
        return SQLAlchemyTransferReader(session)

    @provide(scope=Scope.REQUEST)
    def get_transfer_posting(
        self, ledger: StockLedger, lot_resolver: LotResolver
    ) -> TransferPosting:
        return TransferPosting(ledger=ledger, lot_resolver=lot_resolver)

    @provide(scope=Scope.REQUEST)
    def get_transfer_repository(self, session: AsyncSession) -> TransferRepository:
        return SQLAlchemyTransferRepository(session)


    @provide(scope=Scope.REQUEST)
    def get_inventory_api(
        self,
        create_receipt_interactor: CreateReceiptInteractor,
        post_receipt_interactor: PostReceiptInteractor,
        post_production_interactor: PostProductionInteractor,
        post_sale_interactor: PostSaleInteractor,
        balance_repository: StockBalanceRepository,
        movement_repository: StockMovementRepository,
        business_api: BusinessAPI,
    ) -> InventoryAPI:
        return InventoryAPI(
            create_receipt_interactor=create_receipt_interactor,
            post_receipt_interactor=post_receipt_interactor,
            post_production_interactor=post_production_interactor,
            post_sale_interactor=post_sale_interactor,
            balance_repository=balance_repository,
            movement_repository=movement_repository,
            business_api=business_api,
        )
