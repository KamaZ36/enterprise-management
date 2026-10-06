from uuid import UUID

from myasnaya_derevnya.core.types.permission import Permission
from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.permissions import ASSIGN_ROLES
from myasnaya_derevnya.modules.staff.domain.value_objects.resolved_assignment import (
    ResolvedAssignment,
)


class AccessPolicy:
    def can(
        self,
        permission: Permission,
        target_org_unit_id: UUID | None,
        assignments: list[ResolvedAssignment],
        ancestors_of_target: frozenset[UUID],
    ) -> bool:
        for ra in assignments:
            role = ra.role

            if role.is_wildcard:
                return True

            if permission.code not in role.permission_codes:
                continue

            if ra.assignment.org_unit_id is None:
                return True

            if target_org_unit_id is None:
                continue

            if ra.assignment.org_unit_id == target_org_unit_id:
                return True

            if (
                ra.assignment.include_descendants
                and ra.assignment.org_unit_id in ancestors_of_target
            ):
                return True

        return False

    def can_assign(
        self,
        target_role: Role,
        target_org_unit_id: UUID,
        actor_assignments: list[ResolvedAssignment],
        ancestors_of_target: frozenset[UUID],
    ) -> bool:
        if not target_role.is_assignable:
            return False

        if not self.can(
            permission=ASSIGN_ROLES,
            target_org_unit_id=target_org_unit_id,
            assignments=actor_assignments,
            ancestors_of_target=ancestors_of_target,
        ):
            return False

        actor_is_wildcard = any(ra.role.is_wildcard for ra in actor_assignments)

        if target_role.is_system and not actor_is_wildcard:
            return False

        if actor_is_wildcard:
            return True

        grantable: set[UUID] = set()
        for ra in actor_assignments:
            grantable |= ra.role.grantable_role_ids

        if target_role.id not in grantable:
            return False

        actor_max_level = self._max_level_in_scope(
            assignments=actor_assignments,
            target_org_unit_id=target_org_unit_id,
            ancestors_of_target=ancestors_of_target,
        )

        return target_role.level < actor_max_level

    def _max_level_in_scope(
        self,
        assignments: list[ResolvedAssignment],
        target_org_unit_id: UUID,
        ancestors_of_target: frozenset[UUID],
    ) -> int:
        max_level = 0
        for ra in assignments:
            assignment = ra.assignment
            covers = (
                assignment.org_unit_id is None
                or assignment.org_unit_id == target_org_unit_id
                or (
                    assignment.include_descendants
                    and assignment.org_unit_id in ancestors_of_target
                )
            )
            if covers:
                max_level = max(max_level, ra.role.level)
        return max_level
