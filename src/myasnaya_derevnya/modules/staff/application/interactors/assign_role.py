from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.auth.domain.errors import RoleNotFound
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)
from myasnaya_derevnya.modules.staff.domain.errors import EmployeeNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.employee.base import (
    EmployeeRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


@dataclass(frozen=True, slots=True)
class AssignRoleCommand:
    employee_id: UUID
    role_id: UUID
    org_unit_id: UUID
    include_descendants: bool


class AssignRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        employee_repository: EmployeeRepository,
        role_repository: RoleRepository,
        role_assignment_repository: RoleAssignmentRepository,
        transaction_manager: TransactionManager,
        access_service: AccessService,
    ) -> None:
        self._identity_provider = identity_provider
        self._employee_repository = employee_repository
        self._role_repository = role_repository
        self._role_assignment_repository = role_assignment_repository
        self._transaction_manager = transaction_manager
        self._access_service = access_service

    async def __call__(self, command: AssignRoleCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()
        if not await self._access_service.can(
            user_id=current_user_id,
            permission=MANAGE_ROLES,
            org_unit_id=command.org_unit_id,
        ):
            raise ForbiddenError()

        role = await self._role_repository.get_by_id(role_id=command.role_id)
        if role is None:
            raise RoleNotFound()

        if not await self._access_service.can_assign(
            actor_user_id=current_user_id,
            role_id=role.id,
            org_unit_id=command.org_unit_id,
        ):
            raise ForbiddenError()

        employee = await self._employee_repository.get_by_id(command.employee_id)

        if employee is None:
            raise EmployeeNotFound()

        assigned_role = RoleAssignment.create(
            user_id=employee.user_id,
            role_id=role.id,
            org_unit_id=command.org_unit_id,
            include_descendants=command.include_descendants,
            granted_by=current_user_id,
        )

        await self._role_assignment_repository.add(assigned_role)
        await self._transaction_manager.commit()
