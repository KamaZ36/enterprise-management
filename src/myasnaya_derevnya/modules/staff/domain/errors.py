from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ConflictError, NotFoundError


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


@dataclass(slots=True, eq=False)
class RoleIsSystemError(ConflictError):
    code: str

    def __str__(self) -> str:
        return f"Системную роль «{self.code}» удалить нельзя"


@dataclass(slots=True, eq=False)
class RoleInUseError(ConflictError):
    code: str
    assignments: int

    def __str__(self) -> str:
        return (
            f"Роль «{self.code}» назначена сотрудникам ({self.assignments}) — "
            "сначала отзовите её"
        )
