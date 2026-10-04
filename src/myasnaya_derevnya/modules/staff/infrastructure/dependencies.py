from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.access_serivce import AccessService
from myasnaya_derevnya.modules.staff.application.interactors.create_credential import (
    CreateCredentialEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_employee import (
    CreateEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.sqlalchemy import (
    SQLAlchemyRoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.user_role.base import (
    UserRoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.user_role.sqlalchemy import (
    SQLAlchemyUserRoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.services.access_service import (
    SQLAlchemyAccessService,
)


class StaffDepProvider(Provider):
    # REPOSITORIES
    @provide(scope=Scope.REQUEST)
    def get_role_repository(self, session: AsyncSession) -> RoleRepository:
        return SQLAlchemyRoleRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_role_repository(self, session: AsyncSession) -> UserRoleRepository:
        return SQLAlchemyUserRoleRepository(session)

    # SERVICES
    @provide(scope=Scope.REQUEST)
    def get_access_service(self, session: AsyncSession) -> AccessService:
        return SQLAlchemyAccessService(session)

    # INTERACTORS
    create_employee_interactor = provide(CreateEmployeeInteractor, scope=Scope.REQUEST)

    create_credentials_interactor = provide(
        CreateCredentialEmployeeInteractor, scope=Scope.REQUEST
    )
