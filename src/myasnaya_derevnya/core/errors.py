from dataclasses import dataclass


@dataclass(slots=True, eq=False)
class ProjectError(Exception):
    def __post_init__(self) -> None:
        super().__init__(self.__str__())


@dataclass(slots=True, eq=False)
class AppError(ProjectError):
    def __str__(self) -> str:
        return "Ошибка приложения"


@dataclass(slots=True, eq=False)
class DomainError(ProjectError):
    def __str__(self) -> str:
        return "Ошибка доменного слоя"


@dataclass(slots=True, eq=False)
class UnauthorizedError(AppError): ...


@dataclass(slots=True, eq=False)
class ForbiddenError(AppError): ...


@dataclass(slots=True, eq=False)
class ValidationError(AppError): ...


@dataclass(slots=True, eq=False)
class NotFoundError(AppError): ...


@dataclass(slots=True, eq=False)
class ConflictError(AppError):
    def __str__(self) -> str:
        return "Конфликт: объект с такими данными уже существует"


@dataclass(slots=True, eq=False)
class UniqueViolationError(ConflictError):
    constraint: str | None = None

    def __str__(self) -> str:
        name = self.constraint or "неизвестное ограничение"
        return f"Нарушено ограничение уникальности: {name}"
