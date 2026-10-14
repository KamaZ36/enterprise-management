import secrets
import string
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.presentation.facade import AuthAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import (
    RESET_EMPLOYEE_PASSWORD,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)

PASSWORD_LENGTH = 8


@dataclass(frozen=True, slots=True)
class ResetEmployeePasswordCommand:
    employee_id: UUID


class ResetEmployeePasswordInteractor:
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

    async def __call__(self, command: ResetEmployeePasswordCommand) -> dict[str, str]:
        current_user_id = await self._identity_provider.get_current_user_id()

        employee = await self._employee_repository.get_by_id(command.employee_id)
        if employee is None:
            raise EmployeeNotFound()

        allowed = await self._access_service.can(
            user_id=current_user_id,
            permission=RESET_EMPLOYEE_PASSWORD,
            org_unit_id=employee.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        password = self._generate_password()
        await self._auth_api.reset_employee_password(
            user_id=employee.user_id, password=password
        )

        await self._transaction_manager.commit()

        return {"password": password}

    @staticmethod
    def _generate_password() -> str:
        alphabet = string.ascii_letters + string.digits

        return "".join(secrets.choice(alphabet) for _ in range(PASSWORD_LENGTH))
