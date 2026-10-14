from dataclasses import dataclass, replace

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.dto import EmployeeListItem
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.readers.employee.base import (
    EmployeeReader,
)


@dataclass(frozen=True, slots=True)
class ListEmployeesQuery:
    limit: int = 20
    offset: int = 0
    search: str | None = None


@dataclass(frozen=True, slots=True)
class EmployeePage:
    items: list[EmployeeListItem]
    total: int
    limit: int
    offset: int


class ListEmployeesInteractor:
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

    async def __call__(self, query: ListEmployeesQuery) -> EmployeePage:
        current_user_id = await self._identity_provider.get_current_user_id()

        scope = await self._access_service.scope_for(
            user_id=current_user_id, permission=READ_EMPLOYEES
        )
        if scope.is_empty():
            raise ForbiddenError()

        items, total = await self._employee_reader.list(
            limit=query.limit,
            offset=query.offset,
            search=query.search,
            org_unit_ids=scope.narrow(None),
        )

        return EmployeePage(
            items=await self._with_unit_names(items),
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def _with_unit_names(
        self, items: list[EmployeeListItem]
    ) -> list[EmployeeListItem]:
        if not items:
            return items

        titles = await self._business_api.org_unit_titles(
            {item.org_unit_id for item in items}
        )

        return [
            replace(item, org_unit_name=titles.get(item.org_unit_id)) for item in items
        ]
