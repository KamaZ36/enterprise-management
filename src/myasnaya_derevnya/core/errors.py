from dataclasses import dataclass


@dataclass(frozen=True, slots=True, eq=False)
class ProjectError(Exception):
    """Базовый класс ошибок всего проекта"""

    def __post_init__(self) -> None:
        super().__init__(self.__str__())


@dataclass(frozen=True, slots=True, eq=False)
class AppError(ProjectError):
    """Базовая ошибка прикладного слоя"""

    def __str__(self) -> str:
        return "Ошибка приложения"


@dataclass(frozen=True, slots=True, eq=False)
class DomainError(ProjectError):
    """Базовая ошибка доменного слоя"""

    def __str__(self) -> str:
        return "Ошибка доменного слоя"


@dataclass(frozen=True, slots=True, eq=False)
class UnauthorizedError(AppError): ...


@dataclass(frozen=True, slots=True, eq=False)
class ForbiddenError(AppError): ...


@dataclass(frozen=True, slots=True, eq=False)
class ValidationError(AppError): ...


@dataclass(frozen=True, slots=True, eq=False)
class NotFoundError(AppError): ...
