from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.fiscal.application.interactors.bind_cash_register import (
    BindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.create_cash_register import (
    CreateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.get_cash_register import (
    GetCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_cash_registers import (
    ListCashRegistersInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.list_stock_locations import (
    ListStockLocationsInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.unbind_cash_register import (
    UnbindCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.application.interactors.update_cash_register import (
    UpdateCashRegisterInteractor,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.base import (
    CashRegisterReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.cash_register.sqlalchemy import (
    SQLAlchemyCashRegisterReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.base import (
    CashRegisterRepository,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.cash_register.sqlalchemy import (
    SQLAlchemyCashRegisterRepository,
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
