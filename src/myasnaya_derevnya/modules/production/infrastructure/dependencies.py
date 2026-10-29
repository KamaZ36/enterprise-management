from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.production.application.interactors.cancel_production_order import (
    CancelProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.create_production_order import (
    CreateProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.create_tech_card import (
    CreateTechCardInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.get_production_order import (
    GetProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.get_tech_card import (
    GetTechCardInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.list_production_orders import (
    ListProductionOrdersInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.list_tech_cards import (
    ListTechCardsInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.post_production_order import (
    PostProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.application.interactors.update_production_order import (
    UpdateProductionOrderInteractor,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.production_order.base import (
    ProductionOrderReader,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.production_order.sqlalchemy import (
    SQLAlchemyProductionOrderReader,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.tech_card.base import (
    TechCardReader,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.tech_card.sqlalchemy import (
    SQLAlchemyTechCardReader,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.sqlalchemy import (
    SQLAlchemyProductionOrderRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.base import (
    TechCardRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.repositories.tech_card.sqlalchemy import (
    SQLAlchemyTechCardRepository,
)
from myasnaya_derevnya.modules.production.presentation.production_api import (
    ProductionAPI,
)


class ProductionDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_tech_card_repository(self, session: AsyncSession) -> TechCardRepository:
        return SQLAlchemyTechCardRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_production_order_repository(
        self, session: AsyncSession
    ) -> ProductionOrderRepository:
        return SQLAlchemyProductionOrderRepository(session)


    @provide(scope=Scope.REQUEST)
    def get_tech_card_reader(self, session: AsyncSession) -> TechCardReader:
        return SQLAlchemyTechCardReader(session)

    @provide(scope=Scope.REQUEST)
    def get_production_order_reader(
        self, session: AsyncSession
    ) -> ProductionOrderReader:
        return SQLAlchemyProductionOrderReader(session)

    @provide(scope=Scope.REQUEST)
    def get_production_api(self, tech_card_repository: TechCardRepository) -> ProductionAPI:
        return ProductionAPI(tech_card_repository=tech_card_repository)


    create_tech_card_interactor = provide(CreateTechCardInteractor, scope=Scope.REQUEST)
    list_tech_cards_interactor = provide(ListTechCardsInteractor, scope=Scope.REQUEST)
    get_tech_card_interactor = provide(GetTechCardInteractor, scope=Scope.REQUEST)
    create_production_order_interactor = provide(
        CreateProductionOrderInteractor, scope=Scope.REQUEST
    )
    update_production_order_interactor = provide(
        UpdateProductionOrderInteractor, scope=Scope.REQUEST
    )
    post_production_order_interactor = provide(
        PostProductionOrderInteractor, scope=Scope.REQUEST
    )
    cancel_production_order_interactor = provide(
        CancelProductionOrderInteractor, scope=Scope.REQUEST
    )
    list_production_orders_interactor = provide(
        ListProductionOrdersInteractor, scope=Scope.REQUEST
    )
    get_production_order_interactor = provide(
        GetProductionOrderInteractor, scope=Scope.REQUEST
    )
