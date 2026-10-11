from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.staff.application.dto import (
    CurrentUserRole,
    CurrentUserView,
    EmployeeRoleListItem,
    PermissionItem,
    RoleListItem,
)
from myasnaya_derevnya.modules.staff.domain.entities.employee import Employee


class AssignRoleCommandSchema(BaseModel):
    role_id: UUID
    org_unit_id: UUID
    include_descendants: bool


class EmployeeSchema(BaseModel):
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

    @classmethod
    def from_entity(cls, employee: Employee) -> EmployeeSchema:
        return cls(
            id=employee.id,
            user_id=employee.user_id,
            first_name=employee.first_name,
            last_name=employee.last_name,
            middle_name=employee.middle_name,
            phone_number=str(employee.phone_number) if employee.phone_number else None,
            position=employee.position,
            hired_at=employee.hired_at,
            dismissed_at=employee.dismissed_at,
            is_active=employee.is_active,
        )


class UpdateEmployeeSchema(BaseModel):
    first_name: str | None = Field(default=None, min_length=1)
    last_name: str | None = Field(default=None, min_length=1)
    middle_name: str | None = None
    phone_number: str | None = None
    position: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


class EmployeeListSchema(BaseModel):
    items: list[EmployeeSchema]
    total: int
    limit: int
    offset: int


class RoleSchema(BaseModel):
    id: UUID
    code: str
    name: str
    level: int
    is_system: bool
    is_assignable: bool
    is_wildcard: bool
    permission_codes: list[str]

    @classmethod
    def from_dto(cls, item: RoleListItem) -> RoleSchema:
        return cls(
            id=item.id,
            code=item.code,
            name=item.name,
            level=item.level,
            is_system=item.is_system,
            is_assignable=item.is_assignable,
            is_wildcard=item.is_wildcard,
            permission_codes=sorted(item.permission_codes),
        )


class EmployeeRoleSchema(BaseModel):
    id: UUID
    role_id: UUID
    role_code: str
    role_name: str
    org_unit_id: UUID | None
    include_descendants: bool
    status: str
    assigned_at: datetime

    @classmethod
    def from_dto(cls, item: EmployeeRoleListItem) -> EmployeeRoleSchema:
        return cls(
            id=item.id,
            role_id=item.role_id,
            role_code=item.role_code,
            role_name=item.role_name,
            org_unit_id=item.org_unit_id,
            include_descendants=item.include_descendants,
            status=item.status.value,
            assigned_at=item.assigned_at,
        )


class CurrentUserRoleSchema(BaseModel):
    code: str
    name: str
    org_unit_id: UUID | None

    @classmethod
    def from_dto(cls, item: CurrentUserRole) -> CurrentUserRoleSchema:
        return cls(code=item.code, name=item.name, org_unit_id=item.org_unit_id)


class CurrentUserSchema(BaseModel):
    user_id: UUID
    employee_id: UUID | None
    first_name: str | None
    last_name: str | None
    middle_name: str | None
    position: str | None
    roles: list[CurrentUserRoleSchema]
    permissions: list[str]

    @classmethod
    def from_dto(cls, view: CurrentUserView) -> CurrentUserSchema:
        return cls(
            user_id=view.user_id,
            employee_id=view.employee_id,
            first_name=view.first_name,
            last_name=view.last_name,
            middle_name=view.middle_name,
            position=view.position,
            roles=[CurrentUserRoleSchema.from_dto(item) for item in view.roles],
            permissions=sorted(view.permissions),
        )


class PermissionSchema(BaseModel):
    code: str
    description: str

    @classmethod
    def from_dto(cls, item: PermissionItem) -> PermissionSchema:
        return cls(code=item.code, description=item.description)
