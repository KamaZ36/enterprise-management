from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True, slots=True)
class ListEmployeesQuery:
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    def normalized(self) -> ListEmployeesQuery:
        return ListEmployeesQuery(
            limit=min(max(self.limit, 1), MAX_LIMIT),
            offset=max(self.offset, 0),
        )


@dataclass(frozen=True, slots=True)
class EmployeePage:
    items: list[Employee]
    total: int
    limit: int
    offset: int


class ListEmployeesInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        access_service: AccessService,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._access_service = access_service
        self._business_api = business_api

    async def __call__(self, query: ListEmployeesQuery) -> EmployeePage:
        page = query.normalized()

        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._access_service.can(
            user_id=current_user_id,
            permission=READ_EMPLOYEES,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        items, total = await self._employee_repository.list(
            limit=page.limit, offset=page.offset
        )

        return EmployeePage(
            items=items,
            total=total,
            limit=page.limit,
            offset=page.offset,
        )
