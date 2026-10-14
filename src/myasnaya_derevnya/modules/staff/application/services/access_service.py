from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.domain.services.policy_of_access import (
    AccessPolicy,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
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

    async def scopes_of(
        self, user_id: UUID, permission: Permission
    ) -> list[tuple[UUID | None, bool]]:
        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id=user_id,
        )
        return self._access_policy.scopes_of(
            permission=permission, assignments=assignments
        )

    async def scope_for(self, user_id: UUID, permission: Permission) -> AccessScope:
        """Область действия права: вся компания или конкретные подразделения.

        Единственное место, где разбираются назначения, флаги потомков и дерево.
        Раньше эта логика жила внутри интерактора заказов и грозила расползтись.
        """
        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id=user_id,
        )
        scopes = self._access_policy.scopes_of(
            permission=permission, assignments=assignments
        )

        if any(org_unit_id is None for org_unit_id, _ in scopes):
            return AccessScope.company_wide()

        exact = {
            org_unit_id
            for org_unit_id, descendants in scopes
            if org_unit_id is not None and not descendants
        }
        with_descendants = {
            org_unit_id
            for org_unit_id, descendants in scopes
            if org_unit_id is not None and descendants
        }

        if with_descendants:
            exact |= set(
                await self._business_api.org_unit_descendants_of(with_descendants)
            )

        return AccessScope.of(exact)

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
