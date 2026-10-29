from dishka import Provider, Scope, provide
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import InventoryAPI
from myasnaya_derevnya.modules.pos.application.interactors.create_source import (
    CreatePosSourceInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.delete_product_mapping import (
    DeletePosProductMappingInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.get_receipt import (
    GetPosReceiptInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.import_receipts import (
    ImportPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.issue_agent_key import (
    IssuePosAgentKeyInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_agents import (
    ListPosAgentsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_locations import (
    ListPosLocationsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_product_mappings import (
    ListPosProductMappingsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_receipts import (
    ListPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_sources import (
    ListPosSourcesInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.list_unmapped_products import (
    ListPosUnmappedProductsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.post_pending_receipts import (
    PostPendingPosReceiptsInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.post_receipt import (
    PostPosReceiptInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.register_heartbeat import (
    RegisterHeartbeatInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.rotate_agent_key import (
    RotatePosAgentKeyInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.set_agent_active import (
    SetPosAgentActiveInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.update_source import (
    UpdatePosSourceInteractor,
)
from myasnaya_derevnya.modules.pos.application.interactors.upsert_product_mapping import (
    UpsertPosProductMappingInteractor,
)
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from myasnaya_derevnya.modules.pos.infrastructure.auth import PosAgentAuthenticator
from myasnaya_derevnya.modules.pos.infrastructure.readers.product_map.base import (
    PosProductMapReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.readers.product_map.sqlalchemy import (
    SQLAlchemyPosProductMapReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.readers.receipt.base import (
    PosReceiptReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.readers.receipt.sqlalchemy import (
    SQLAlchemyPosReceiptReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.sqlalchemy import (
    SQLAlchemyPosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.import_batch.base import (
    PosImportBatchRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.import_batch.sqlalchemy import (
    SQLAlchemyPosImportBatchRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.base import (
    PosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.sqlalchemy import (
    SQLAlchemyPosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.sqlalchemy import (
    SQLAlchemyPosReceiptRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.sqlalchemy import (
    SQLAlchemyPosSourceRepository,
)
from myasnaya_derevnya.modules.production.presentation.production_api import (
    ProductionAPI,
)


class PosDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_source_repository(self, session: AsyncSession) -> PosSourceRepository:
        return SQLAlchemyPosSourceRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_agent_repository(self, session: AsyncSession) -> PosAgentRepository:
        return SQLAlchemyPosAgentRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_import_batch_repository(
        self, session: AsyncSession
    ) -> PosImportBatchRepository:
        return SQLAlchemyPosImportBatchRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_product_map_repository(
        self, session: AsyncSession
    ) -> PosProductMapRepository:
        return SQLAlchemyPosProductMapRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_receipt_repository(self, session: AsyncSession) -> PosReceiptRepository:
        return SQLAlchemyPosReceiptRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_receipt_reader(self, session: AsyncSession) -> PosReceiptReader:
        return SQLAlchemyPosReceiptReader(session)

    @provide(scope=Scope.REQUEST)
    def get_product_map_reader(self, session: AsyncSession) -> PosProductMapReader:
        return SQLAlchemyPosProductMapReader(session)

    @provide(scope=Scope.REQUEST)
    def get_posting_service(
        self,
        receipt_repository: PosReceiptRepository,
        inventory_api: InventoryAPI,
        production_api: ProductionAPI,
        transaction_manager: TransactionManager,
    ) -> ReceiptPostingService:
        return ReceiptPostingService(
            receipt_repository=receipt_repository,
            inventory_api=inventory_api,
            production_api=production_api,
            transaction_manager=transaction_manager,
        )

    @provide(scope=Scope.REQUEST)
    def get_agent_authenticator(
        self,
        request: Request,
        agent_repository: PosAgentRepository,
        source_repository: PosSourceRepository,
        transaction_manager: TransactionManager,
    ) -> PosAgentAuthenticator:
        return PosAgentAuthenticator(
            request=request,
            agent_repository=agent_repository,
            source_repository=source_repository,
            transaction_manager=transaction_manager,
        )

    create_source_interactor = provide(CreatePosSourceInteractor, scope=Scope.REQUEST)
    update_source_interactor = provide(UpdatePosSourceInteractor, scope=Scope.REQUEST)
    list_sources_interactor = provide(ListPosSourcesInteractor, scope=Scope.REQUEST)
    list_locations_interactor = provide(
        ListPosLocationsInteractor, scope=Scope.REQUEST
    )
    issue_agent_key_interactor = provide(
        IssuePosAgentKeyInteractor, scope=Scope.REQUEST
    )
    rotate_agent_key_interactor = provide(
        RotatePosAgentKeyInteractor, scope=Scope.REQUEST
    )
    set_agent_active_interactor = provide(
        SetPosAgentActiveInteractor, scope=Scope.REQUEST
    )
    list_agents_interactor = provide(ListPosAgentsInteractor, scope=Scope.REQUEST)
    import_receipts_interactor = provide(
        ImportPosReceiptsInteractor, scope=Scope.REQUEST
    )
    register_heartbeat_interactor = provide(
        RegisterHeartbeatInteractor, scope=Scope.REQUEST
    )
    list_receipts_interactor = provide(ListPosReceiptsInteractor, scope=Scope.REQUEST)
    get_receipt_interactor = provide(GetPosReceiptInteractor, scope=Scope.REQUEST)
    post_receipt_interactor = provide(PostPosReceiptInteractor, scope=Scope.REQUEST)
    post_pending_receipts_interactor = provide(
        PostPendingPosReceiptsInteractor, scope=Scope.REQUEST
    )
    list_product_mappings_interactor = provide(
        ListPosProductMappingsInteractor, scope=Scope.REQUEST
    )
    list_unmapped_products_interactor = provide(
        ListPosUnmappedProductsInteractor, scope=Scope.REQUEST
    )
    upsert_product_mapping_interactor = provide(
        UpsertPosProductMappingInteractor, scope=Scope.REQUEST
    )
    delete_product_mapping_interactor = provide(
        DeletePosProductMappingInteractor, scope=Scope.REQUEST
    )
