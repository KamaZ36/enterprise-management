from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.access_serivce import AccessService
from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.domain.errors import RoleNotFound
from myasnaya_derevnya.modules.staff.domain.entities.user_role import UserRole
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.user_role.base import (
    UserRoleRepository,
)


@dataclass(frozen=True, slots=True)
class AssignRoleCommand:
    employee_id: UUID
    role_id: UUID
    target_location_id: UUID | None


class AssignRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        role_repository: RoleRepository,
        user_role_repository: UserRoleRepository,
        transaction_manager: TransactionManager,
        access_service: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._role_repository = role_repository
        self._user_role_repository = user_role_repository
        self._transaction_manager = transaction_manager
        self._access_service = access_service

    async def __call__(self, command: AssignRoleCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()
        await self._access_service.require(
            user_id=current_user_id,
            permission=MANAGE_ROLES,
            location_id=command.target_location_id,
        )

        employee = await self._employee_repository.get_by_id(command.employee_id)

        if employee is None:
            raise EmployeeNotFound()

        role = await self._role_repository.get_by_id(role_id=command.role_id)

        if role is None:
            raise RoleNotFound()

        assigned_role = UserRole.create(
            user_id=employee.user_id,
            role_id=role.id,
            location_id=command.target_location_id,
            created_by=current_user_id,
        )

        await self._user_role_repository.add(assigned_role)
        await self._transaction_manager.commit()
