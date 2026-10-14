from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.sales.application.interactors.cancel_order import (
    CancelOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.complete_order import (
    CompleteOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.confirm_order import (
    ConfirmOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.create_order import (
    CreateOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.get_my_order import (
    GetMyOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.get_order import (
    GetOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.list_my_orders import (
    ListMyOrdersInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.list_orders import (
    ListOrdersInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.mark_order_ready import (
    MarkOrderReadyInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.start_preparing_order import (
    StartPreparingOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.interactors.update_order import (
    UpdateOrderInteractor,
)
from myasnaya_derevnya.modules.sales.application.services.order_access import (
    OrderAccess,
)
from myasnaya_derevnya.modules.sales.infrastructure.readers.order.base import (
    OrderReader,
)
from myasnaya_derevnya.modules.sales.infrastructure.readers.order.sqlalchemy import (
    SQLAlchemyOrderReader,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.sqlalchemy import (
    SQLAlchemyOrderRepository,
)


class SalesDepProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_order_repository(self, session: AsyncSession) -> OrderRepository:
        return SQLAlchemyOrderRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_order_reader(self, session: AsyncSession) -> OrderReader:
        return SQLAlchemyOrderReader(session)

    list_orders_interactor = provide(ListOrdersInteractor, scope=Scope.REQUEST)
    list_my_orders_interactor = provide(ListMyOrdersInteractor, scope=Scope.REQUEST)
    get_my_order_interactor = provide(GetMyOrderInteractor, scope=Scope.REQUEST)
    get_order_interactor = provide(GetOrderInteractor, scope=Scope.REQUEST)
    order_access = provide(OrderAccess, scope=Scope.REQUEST)
    create_order_interactor = provide(CreateOrderInteractor, scope=Scope.REQUEST)
    confirm_order_interactor = provide(ConfirmOrderInteractor, scope=Scope.REQUEST)
    cancel_order_interactor = provide(CancelOrderInteractor, scope=Scope.REQUEST)
    complete_order_interactor = provide(CompleteOrderInteractor, scope=Scope.REQUEST)
    update_order_interactor = provide(UpdateOrderInteractor, scope=Scope.REQUEST)
    start_preparing_order_interactor = provide(
        StartPreparingOrderInteractor, scope=Scope.REQUEST
    )
    mark_order_ready_interactor = provide(MarkOrderReadyInteractor, scope=Scope.REQUEST)
