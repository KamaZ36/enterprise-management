from dataclasses import dataclass

from myasnaya_derevnya.modules.staff.domain.entities.role import Role
from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignment,
)


@dataclass(frozen=True, slots=True)
class ResolvedAssignment:
    assignment: RoleAssignment
    role: Role
