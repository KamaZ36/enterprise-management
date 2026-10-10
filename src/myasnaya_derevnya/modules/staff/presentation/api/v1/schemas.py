from datetime import date
from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.staff.application.dto import RoleListItem
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
        )
