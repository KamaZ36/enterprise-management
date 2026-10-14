from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from myasnaya_derevnya.modules.staff.domain.entities.role_assignment import (
    RoleAssignmentStatus,
)


@dataclass(frozen=True, slots=True)
class EmployeeListItem:
    id: UUID
    user_id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    phone_number: str | None
    position: str
    hired_at: date
    dismissed_at: date | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class RoleListItem:
    id: UUID
    code: str
    name: str
    description: str | None
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
    scopes: tuple[CurrentUserScope, ...] = ()


@dataclass(frozen=True, slots=True)
class PermissionItem:
    code: str
    description: str


@dataclass(frozen=True, slots=True)
class CurrentUserScope:
    id: UUID
    title: str
