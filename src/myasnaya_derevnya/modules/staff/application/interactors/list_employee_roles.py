from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.staff.application.dto import EmployeeRoleListItem
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee.base import (
    EmployeeReader,
)
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee_role.base import (
    EmployeeRoleReader,
)


@dataclass(frozen=True, slots=True)
class ListEmployeeRolesQuery:
    employee_id: UUID


class ListEmployeeRolesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_reader: EmployeeReader,
        employee_role_reader: EmployeeRoleReader,
        access_service: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_reader = employee_reader
        self._employee_role_reader = employee_role_reader
        self._access_service = access_service

    async def __call__(
        self, query: ListEmployeeRolesQuery
    ) -> list[EmployeeRoleListItem]:
        current_user_id = await self._identity_provider.get_current_user_id()

        scope = await self._access_service.scope_for(
            user_id=current_user_id, permission=READ_EMPLOYEES
        )
        if scope.is_empty():
            raise ForbiddenError()

        employee = await self._employee_reader.get_by_id(
            query.employee_id, org_unit_ids=scope.narrow(None)
        )
        if employee is None:
            raise EmployeeNotFound()

        return await self._employee_role_reader.list_active_for_user(employee.user_id)
