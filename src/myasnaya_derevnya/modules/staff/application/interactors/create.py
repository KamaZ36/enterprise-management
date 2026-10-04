from dataclasses import dataclass
from datetime import date
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.core.types.phone_number import PhoneNumber
from myasnaya_derevnya.modules.auth.presentation.facade import AuthFacade
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee
from myasnaya_derevnya.modules.staff.domain.permissions import CREATE_EMPLOYEE
from myasnaya_derevnya.modules.staff.infrastructure.employee.base import (
    EmployeeRepository,
)


@dataclass(frozen=True, slots=True)
class CreateEmployeeCommand:
    first_name: str
    last_name: str
    middle_name: str | None
    phone_number: str
    position: str
    hired_at: date
    location_id: UUID


class CreateEmployeeInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        transaction_manager: TransactionManager,
        auth_api: AuthFacade,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._transaction_manager = transaction_manager
        self._auth_api = auth_api

    async def __call__(self, command: CreateEmployeeCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()
        await self._auth_api.require(
            user_id=current_user_id,
            location_id=command.location_id,
            permission=CREATE_EMPLOYEE,
        )

        phone_number = PhoneNumber.parse(command.phone_number)

        employee = Employee.create(
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
