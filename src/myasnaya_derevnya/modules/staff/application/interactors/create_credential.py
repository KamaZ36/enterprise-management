import secrets
import string
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.access_serivce import AccessService
from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_EMPLOYEES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)


@dataclass(frozen=True, slots=True)
class CreateCredentialEmployeeCommand:
    employee_id: UUID
    username: str


class CreateCredentialEmployeeInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        access_service: AccessService,
        auth_api: AuthAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._access_service = access_service
        self._auth_api = auth_api
        self._transaction_manager = transaction_manager

    async def __call__(
        self, command: CreateCredentialEmployeeCommand
    ) -> dict[str, str]:
        current_user_id = await self._identity_provider.get_current_user_id()
        await self._access_service.require(
            user_id=current_user_id,
            permission=MANAGE_EMPLOYEES,
            location_id=None,
        )

        employee = await self._employee_repository.get_by_id(command.employee_id)
        if employee is None:
            raise EmployeeNotFound()

        password = await self._generate_password()
        await self._auth_api.create_employee_credential(
            user_id=employee.user_id, username=command.username, password=password
        )

        await self._transaction_manager.commit()

        return {"username": command.username, "password": password}

    async def _generate_password(self) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(8))
