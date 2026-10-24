import httpx
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.settings.ofd import OfdSettings
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.fiscal.application.interactors.bind_cash_register import (
    BindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.create_cash_register import (
    CreateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.get_cash_register import (
    GetCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.get_ofd_receipt import (
    GetOfdReceiptInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_cash_registers import (
    ListCashRegistersInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_ofd_receipts import (
    ListOfdReceiptsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_stock_locations import (
    ListStockLocationsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.map_ofd_receipt_line import (
    MapOfdReceiptLineInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ofd_receipt import (
    PostOfdReceiptInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.post_ready_ofd_receipts import (
    PostReadyOfdReceiptsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.sync_ofd_receipts import (
    SyncOfdReceiptsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.unbind_cash_register import (
    UnbindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.update_cash_register import (
    UpdateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.services.ofd_sync import (
    OfdSyncService,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.ofd.client import OfdClient
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.base import (
    CashRegisterReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.sqlalchemy import (
    SQLAlchemyCashRegisterReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.base import (
    OfdReceiptReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.sqlalchemy import (
    SQLAlchemyOfdReceiptReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.sqlalchemy import (
    SQLAlchemyCashRegisterRepository,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.base import (
    OfdReceiptRepository,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.sqlalchemy import (
    SQLAlchemyOfdReceiptRepository,
)
from myasnaya_derevnya.modules.fiscal.presentation.fiscal_api import FiscalAPI


class FiscalDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_cash_register_repository(
        self, session: AsyncSession
    ) -> CashRegisterRepository:
        return SQLAlchemyCashRegisterRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_cash_register_reader(self, session: AsyncSession) -> CashRegisterReader:
        return SQLAlchemyCashRegisterReader(session)

    @provide(scope=Scope.REQUEST)
    def get_ofd_receipt_repository(
        self, session: AsyncSession
    ) -> OfdReceiptRepository:
        return SQLAlchemyOfdReceiptRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_ofd_receipt_reader(
        self, session: AsyncSession
    ) -> OfdReceiptReader:
        return SQLAlchemyOfdReceiptReader(session)

    @provide(scope=Scope.REQUEST)
    def get_ofd_client(
        self, http_client: httpx.AsyncClient, settings: OfdSettings
    ) -> OfdClient:
        return OfdClient(http_client=http_client, settings=settings)

    @provide(scope=Scope.REQUEST)
    def get_ofd_sync_service(
        self,
        ofd_client: OfdClient,
        settings: OfdSettings,
        fiscal_api: FiscalAPI,
        catalog_api: CatalogAPI,
        receipt_repository: OfdReceiptRepository,
        transaction_manager: TransactionManager,
    ) -> OfdSyncService:
        return OfdSyncService(
            ofd_client=ofd_client,
            settings=settings,
            fiscal_api=fiscal_api,
            catalog_api=catalog_api,
            receipt_repository=receipt_repository,
            transaction_manager=transaction_manager,
        )

    @provide(scope=Scope.REQUEST)
    def get_fiscal_api_facade(
        self, cash_register_repository: CashRegisterRepository
    ) -> FiscalAPI:
        return FiscalAPI(cash_register_repository=cash_register_repository)

    create_cash_register_interactor = provide(
        CreateCashRegisterInteractor, scope=Scope.REQUEST
    )
    update_cash_register_interactor = provide(
        UpdateCashRegisterInteractor, scope=Scope.REQUEST
    )
    list_cash_registers_interactor = provide(
        ListCashRegistersInteractor, scope=Scope.REQUEST
    )
    list_stock_locations_interactor = provide(
        ListStockLocationsInteractor, scope=Scope.REQUEST
    )
    get_cash_register_interactor = provide(
        GetCashRegisterInteractor, scope=Scope.REQUEST
    )
    bind_cash_register_interactor = provide(
        BindCashRegisterInteractor, scope=Scope.REQUEST
    )
    unbind_cash_register_interactor = provide(
        UnbindCashRegisterInteractor, scope=Scope.REQUEST
    )
    sync_ofd_receipts_interactor = provide(
        SyncOfdReceiptsInteractor, scope=Scope.REQUEST
    )
    list_ofd_receipts_interactor = provide(
        ListOfdReceiptsInteractor, scope=Scope.REQUEST
    )
    get_ofd_receipt_interactor = provide(
        GetOfdReceiptInteractor, scope=Scope.REQUEST
    )
    map_ofd_receipt_line_interactor = provide(
        MapOfdReceiptLineInteractor, scope=Scope.REQUEST
    )
    post_ofd_receipt_interactor = provide(
        PostOfdReceiptInteractor, scope=Scope.REQUEST
    )
    post_ready_ofd_receipts_interactor = provide(
        PostReadyOfdReceiptsInteractor, scope=Scope.REQUEST
    )
