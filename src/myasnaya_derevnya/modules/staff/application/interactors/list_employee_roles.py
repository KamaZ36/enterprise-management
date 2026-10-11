from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.dto import EmployeeRoleListItem
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee_role.base import (
    EmployeeRoleReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)


@dataclass(frozen=True, slots=True)
class ListEmployeeRolesQuery:
    employee_id: UUID


class ListEmployeeRolesInteractor:
    """Что назначено сотруднику сейчас: без этого роли не отозвать."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        employee_role_reader: EmployeeRoleReader,
        access_service: AccessService,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._employee_role_reader = employee_role_reader
        self._access_service = access_service
        self._business_api = business_api

    async def __call__(
        self, query: ListEmployeeRolesQuery
    ) -> list[EmployeeRoleListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._access_service.can(
            user_id=current_user_id,
            permission=READ_EMPLOYEES,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        employee = await self._employee_repository.get_by_id(query.employee_id)
        if employee is None:
            raise EmployeeNotFound()

        return await self._employee_role_reader.list_active_for_user(employee.user_id)
