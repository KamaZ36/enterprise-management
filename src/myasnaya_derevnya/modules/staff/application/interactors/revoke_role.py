from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.application.services.access_service import (
    AccessService,
)
from myasnaya_derevnya.modules.staff.domain.errors import RoleAssignmentNotFound
from myasnaya_derevnya.modules.staff.domain.permissions import ASSIGN_ROLES
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


@dataclass(frozen=True, slots=True)
class RevokeRoleCommand:
    assignment_id: UUID


class RevokeRoleInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        role_assignment_repository: RoleAssignmentRepository,
        transaction_manager: TransactionManager,
        access_service: AccessService,
        business_api: BusinessAPI,
    ) -> None:
        self._identity_provider = identity_provider
        self._role_assignment_repository = role_assignment_repository
        self._transaction_manager = transaction_manager
        self._access_service = access_service
        self._business_api = business_api

    async def __call__(self, command: RevokeRoleCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        assignment = await self._role_assignment_repository.get_by_id(
            command.assignment_id
        )
        if assignment is None:
            raise RoleAssignmentNotFound(command.assignment_id)

        target_org_unit_id = (
            assignment.org_unit_id or await self._business_api.get_root_unit_id()
        )

        if not await self._access_service.can(
            user_id=current_user_id,
            permission=ASSIGN_ROLES,
            org_unit_id=target_org_unit_id,
        ):
            raise ForbiddenError()

        assignment.revoke()

        await self._role_assignment_repository.save(assignment)
        await self._transaction_manager.commit()
