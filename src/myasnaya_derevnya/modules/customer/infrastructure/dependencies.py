from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.customer.application.interactors.ensure_customer_profile import (
    EnsureCustomerProfileInteractor,
)
from myasnaya_derevnya.modules.customer.application.interactors.login_customer import (
    LoginCustomerInteractor,
)
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.base import (
    CustomerRepository,
)
from myasnaya_derevnya.modules.customer.infrastructure.repositories.customer.sqlalchemy import (
    SQLAlchemyCustomerRepository,
)
from myasnaya_derevnya.modules.customer.presentation.customer_api import CustomerAPI


class CustomerDepProvider(Provider):
    # REPOSITORIES
    @provide(scope=Scope.REQUEST)
    def get_customer_repository(self, session: AsyncSession) -> CustomerRepository:
        return SQLAlchemyCustomerRepository(session)

    # INTERACTORS
    ensure_customer_profile_interactor = provide(
        EnsureCustomerProfileInteractor, scope=Scope.REQUEST
    )

    login_customer_interactor = provide(LoginCustomerInteractor, scope=Scope.REQUEST)

    # FACADE
    customer_api = provide(CustomerAPI, scope=Scope.REQUEST)
