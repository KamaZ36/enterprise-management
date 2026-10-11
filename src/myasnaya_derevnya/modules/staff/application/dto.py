from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignmentStatus,
)


@dataclass(frozen=True, slots=True)
class RoleListItem:
    id: UUID
    code: str
    name: str
    level: int
    is_system: bool
    is_assignable: bool
    is_wildcard: bool
    permission_codes: frozenset[str]


@dataclass(frozen=True, slots=True)
class EmployeeRoleListItem:
    id: UUID
    role_id: UUID
    role_code: str
    role_name: str
    org_unit_id: UUID | None
    include_descendants: bool
    status: RoleAssignmentStatus
    assigned_at: datetime


@dataclass(frozen=True, slots=True)
class CurrentUserRole:
    code: str
    name: str
    org_unit_id: UUID | None


@dataclass(frozen=True, slots=True)
class CurrentUserView:
    user_id: UUID
    employee_id: UUID | None
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    position: str | None
    roles: list[CurrentUserRole]
    permissions: frozenset[str]


@dataclass(frozen=True, slots=True)
class PermissionItem:
    code: str
    description: str
