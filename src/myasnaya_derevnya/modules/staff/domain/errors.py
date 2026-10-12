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
        return f"Системная роль «{self.code}»: её нельзя удалить или изменить"


@dataclass(slots=True, eq=False)
class RoleInUseError(ConflictError):
    code: str
    assignments: int

    def __str__(self) -> str:
        return (
            f"Роль «{self.code}» назначена сотрудникам ({self.assignments}) — "
            "сначала отзовите её"
        )


@dataclass(slots=True, eq=False)
class UnknownPermissionError(ConflictError):
    code: str

    def __str__(self) -> str:
        return f"Права с кодом '{self.code}' не существует."
