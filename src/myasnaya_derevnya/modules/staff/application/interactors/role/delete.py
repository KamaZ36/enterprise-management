import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import (
    RoleInUseError,
    RoleIsSystemError,
    RoleNotFound,
)
from myasnaya_derevnya.modules.staff.domain.permissions import MANAGE_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeleteRoleCommand:
    role_id: UUID


class DeleteRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        role_repository: RoleRepository,
        role_assignment_repository: RoleAssignmentRepository,
        access_service: AccessService,
        business_api: BusinessAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._role_repository = role_repository
        self._role_assignment_repository = role_assignment_repository
        self._access_service = access_service
        self._business_api = business_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: DeleteRoleCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()
        root_org_unit_id = await self._business_api.get_root_unit_id()

        allowed = await self._access_service.can(
            user_id=current_user_id,
            permission=MANAGE_ROLES,
            org_unit_id=root_org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        role = await self._role_repository.get_by_id(command.role_id)
        if role is None:
            raise RoleNotFound(command.role_id)

        if role.is_system:
            raise RoleIsSystemError(role.code)

        assignments = await self._role_assignment_repository.count_active_for_role(
            command.role_id
        )
        if assignments:
            raise RoleInUseError(role.code, assignments)

        await self._role_repository.delete(command.role_id)
        await self._transaction_manager.commit()

        logger.info(
            "Удалена роль",
            extra={"role_id": str(role.id), "code": role.code},
        )
