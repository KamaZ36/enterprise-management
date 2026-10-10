from dataclasses import dataclass
from datetime import date
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)


@dataclass(frozen=True, slots=True)
class CreateEmployeeCommand:
    first_name: str
    last_name: str
    middle_name: str | None
    phone_number: str | None
    position: str
    hired_at: date


class CreateEmployeeInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        transaction_manager: TransactionManager,
        business_api: BusinessAPI,
        access_service: AccessService,
        auth_api: AuthAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._transaction_manager = transaction_manager
        self._business_api = business_api
        self._access_service = access_service
        self._auth_api = auth_api

    async def __call__(self, command: CreateEmployeeCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()
        if not await self._access_service.can(
            user_id=current_user_id,
            permission=MANAGE_EMPLOYEES,
            org_unit_id=root_org_unit_id,
        ):
            raise ForbiddenError()

        phone_number = (
            PhoneNumber.parse(command.phone_number) if command.phone_number else None
        )

        user_id = await self._auth_api.create_user()

        employee = Employee.create(
            user_id=user_id,
            org_unit_id=root_org_unit_id,
            first_name=command.first_name,
            last_name=command.last_name,
            middle_name=command.middle_name,
            phone_number=phone_number,
            position=command.position,
            hired_at=command.hired_at,
        )

        await self._employee_repository.add(employee)
        await self._transaction_manager.commit()

        return employee.id
