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
            if not self._covers(ra.assignment, target_org_unit_id, ancestors_of_target):
                continue
            if ra.role.is_wildcard or permission.code in ra.role.permission_codes:
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

        covering = [
            ra
            for ra in actor_assignments
            if self._covers(ra.assignment, target_org_unit_id, ancestors_of_target)
        ]
        if not covering:
            return False

        if not self.can(
            ASSIGN_ROLES, target_org_unit_id, covering, ancestors_of_target
        ):
            return False

        if any(ra.role.is_wildcard for ra in covering):
            return True

        if target_role.is_system:
            return False

        grantable: set[UUID] = set()
        for ra in covering:
            grantable |= ra.role.grantable_role_ids
        if target_role.id not in grantable:
            return False

        actor_max_level = max(ra.role.level for ra in covering)
        return target_role.level < actor_max_level

    @staticmethod
    def _covers(
        assignment,
        target_org_unit_id: UUID | None,
        ancestors_of_target: frozenset[UUID],
    ) -> bool:
        scope = assignment.org_unit_id
        if scope is None:
            return True
        if target_org_unit_id is None:
            return False
        if scope == target_org_unit_id:
            return True
        return assignment.include_descendants and scope in ancestors_of_target
