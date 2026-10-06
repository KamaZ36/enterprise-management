from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import READ_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)


@dataclass(frozen=True, slots=True)
class GetEmployeeByIdQuery:
    employee_id: UUID
    org_unit_id: UUID


class GetEmployeeByIdInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        access_service: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._access_service = access_service

    async def __call__(self, command: GetEmployeeByIdQuery) -> Employee:
        current_user_id = await self._identity_provider.get_current_user_id()
        if not self._access_service.can(
            user_id=current_user_id,
            permission=READ_EMPLOYEES,
            org_unit_id=command.org_unit_id,
        ):
            raise ForbiddenError()

        employeee = await self._employee_repository.get_by_id(command.employee_id)

        if employeee is None:
            raise EmployeeNotFound()

        return employeee
