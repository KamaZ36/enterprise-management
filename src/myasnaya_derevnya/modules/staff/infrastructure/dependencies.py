from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.staff.application.interactors.assign_role import (
    AssignRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_credential import (
    CreateCredentialEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_employee import (
    CreateEmployeeInteractor,
)
from myasnaya_derevnya.modules.staff.application.interactors.create_role import (
    CreateEmployeeRoleInteractor,
)
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.services.policy_of_access import (
    AccessPolicy,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.sqlalchemy import (
    SQLAlchemyEmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.sqlalchemy import (
    SQLAlchemyRoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.sqlalchemy import (
    SQLAlchemyRoleAssignmentRepository,
)


class StaffDepProvider(Provider):
    # REPOSITORIES
    @provide(scope=Scope.REQUEST)
    def get_role_repository(self, session: AsyncSession) -> RoleRepository:
        return SQLAlchemyRoleRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_user_role_repository(
        self, session: AsyncSession
    ) -> RoleAssignmentRepository:
        return SQLAlchemyRoleAssignmentRepository(session)

    @provide(scope=Scope.REQUEST)
    def get_employee_repository(self, session: AsyncSession) -> EmployeeRepository:
        return SQLAlchemyEmployeeRepository(session)

    # SERVICES

    access_policy = provide(AccessPolicy, scope=Scope.REQUEST)

    acess_service = provide(AccessService, scope=Scope.REQUEST)

    # INTERACTORS
    create_employee_interactor = provide(CreateEmployeeInteractor, scope=Scope.REQUEST)

    create_credentials_interactor = provide(
        CreateCredentialEmployeeInteractor, scope=Scope.REQUEST
    )

    create_employee_role_interactor = provide(
        CreateEmployeeRoleInteractor, scope=Scope.REQUEST
    )

    assign_role_interactor = provide(AssignRoleInteractor, scope=Scope.REQUEST)
