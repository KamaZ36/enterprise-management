from dataclasses import dataclass, replace
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.dto import EmployeeListItem
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee.base import (
    EmployeeReader,
)


@dataclass(frozen=True, slots=True)
class GetEmployeeByIdQuery:
    employee_id: UUID


class GetEmployeeByIdInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_reader: EmployeeReader,
        access_service: AccessService,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_reader = employee_reader
        self._access_service = access_service
        self._business_api = business_api

    async def __call__(self, query: GetEmployeeByIdQuery) -> EmployeeListItem:
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

        titles = await self._business_api.org_unit_titles({employee.org_unit_id})

        return replace(
            employee, org_unit_name=titles.get(employee.org_unit_id)
        )
