from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.domain.services.policy_of_access import (
    AccessPolicy,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


class AccessService:
    def __init__(
        self,
        role_repository: RoleRepository,
        role_assignment_repository: RoleAssignmentRepository,
        business_api: BusinessAPI,
        access_policy: AccessPolicy,
    ) -> None:
        self._role_repository = role_repository
        self._role_assignment_repository = role_assignment_repository
        self._business_api = business_api
        self._access_policy = access_policy

    async def can(
        self,
        user_id: UUID,
        permission: Permission,
        org_unit_id: UUID | None,
    ) -> bool:
        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id=user_id,
        )
        ancestors = await self._load_ancestors(org_unit_id)
        return self._access_policy.can(
            permission=permission,
            target_org_unit_id=org_unit_id,
            assignments=assignments,
            ancestors_of_target=ancestors,
        )

    async def can_assign(
        self,
        actor_user_id: UUID,
        role_id: UUID,
        org_unit_id: UUID,
    ) -> bool:
        target_role = await self._role_repository.get_by_id(role_id)
        if target_role is None:
            return False

        actor_assignments = await self._role_assignment_repository.load_active_for_user(
            user_id=actor_user_id,
        )

        ancestors = await self._load_ancestors(org_unit_id)

        return self._access_policy.can_assign(
            target_role=target_role,
            target_org_unit_id=org_unit_id,
            actor_assignments=actor_assignments,
            ancestors_of_target=ancestors,
        )

    async def _load_ancestors(self, org_unit_id: UUID | None) -> frozenset[UUID]:
        if org_unit_id is None:
            return frozenset()
        return await self._business_api.org_unit_ancestors_of(org_unit_id)
