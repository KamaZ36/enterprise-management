from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.current_scope import CurrentScope
from myasnaya_derevnya.core.permissions import all_permissions
from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.services.policy_of_access import (
    AccessPolicy,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.access_scope import (
    AccessScope,
)
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role.base import (
    RoleRepository,
)
from myasnaya_derevnya.modules.staff.infrastructure.repositories.role_assignment.base import (
    RoleAssignmentRepository,
)


@dataclass(frozen=True, slots=True)
class AccessMap:
    scope: AccessScope
    permissions: frozenset[str]
    by_unit: dict[UUID, frozenset[str]]


class AccessService:
    def __init__(
        self,
        role_repository: RoleRepository,
        role_assignment_repository: RoleAssignmentRepository,
        business_api: BusinessAPI,
        access_policy: AccessPolicy,
        current_scope: CurrentScope,
    ) -> None:
        self._role_repository = role_repository
        self._role_assignment_repository = role_assignment_repository
        self._business_api = business_api
        self._access_policy = access_policy
        self._current_scope = current_scope

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
        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id=user_id,
        )
        scopes = self._access_policy.scopes_of(
            permission=permission, assignments=assignments
        )

        return self._narrow_to_current(await self._resolve_scope(scopes))

    async def access_map(self, user_id: UUID) -> AccessMap:
        assignments = await self._role_assignment_repository.load_active_for_user(
            user_id=user_id,
        )

        return await self._build_access_map(assignments)

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

    async def _build_access_map(
        self, assignments: list[ResolvedAssignment]
    ) -> AccessMap:
        company_wide = any(
            item.assignment.org_unit_id is None for item in assignments
        )
        per_unit: dict[UUID, set[str]] = {}
        union: set[str] = set()

        for item in assignments:
            codes = _role_permission_codes(item.role)
            union |= codes

            unit_id = item.assignment.org_unit_id
            if unit_id is None:
                continue

            if not item.assignment.include_descendants:
                per_unit.setdefault(unit_id, set()).update(codes)
                continue

            covered_units = await self._business_api.org_unit_descendants_of(
                {unit_id}
            )
            if await self._business_api.get_root_unit_id() in covered_units:
                company_wide = True
                continue

            for covered in covered_units:
                per_unit.setdefault(covered, set()).update(codes)

        if company_wide:
            return AccessMap(
                scope=AccessScope.company_wide(),
                permissions=frozenset(union),
                by_unit={},
            )

        return AccessMap(
            scope=AccessScope.of(per_unit),
            permissions=frozenset(union),
            by_unit={unit_id: frozenset(codes) for unit_id, codes in per_unit.items()},
        )

    async def _resolve_scope(
        self, scopes: list[tuple[UUID | None, bool]]
    ) -> AccessScope:
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
            expanded = await self._business_api.org_unit_descendants_of(
                with_descendants
            )


            if await self._business_api.get_root_unit_id() in expanded:
                return AccessScope.company_wide()

            exact |= set(expanded)

        return AccessScope.of(exact)

    def _narrow_to_current(self, base: AccessScope) -> AccessScope:
        requested = self._current_scope.org_unit_id()
        if requested is None:
            return base

        if not base.covers(requested):
            return AccessScope.of([])

        return AccessScope.of([requested])

    async def _load_ancestors(self, org_unit_id: UUID | None) -> frozenset[UUID]:
        if org_unit_id is None:
            return frozenset()
        return await self._business_api.org_unit_ancestors_of(org_unit_id)


def _role_permission_codes(role: Role) -> frozenset[str]:
    if role.is_wildcard:
        return frozenset(permission.code for permission in all_permissions())

    return role.permission_codes
