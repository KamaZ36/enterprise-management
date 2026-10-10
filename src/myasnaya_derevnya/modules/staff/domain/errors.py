from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import NotFoundError


class EmployeeNotFound(NotFoundError): ...


@dataclass(slots=True, eq=False)
class RoleNotFound(NotFoundError):
    role_id: UUID

    def __str__(self) -> str:
        return f"Роль {self.role_id} не найдена."


@dataclass(slots=True, eq=False)
class RoleAssignmentNotFound(NotFoundError):
    assignment_id: UUID

    def __str__(self) -> str:
        return f"Назначение роли {self.assignment_id} не найдено."
