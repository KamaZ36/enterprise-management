from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import DomainError, NotFoundError


class EdoDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка документа ЭДО"


@dataclass(slots=True, eq=False)
class EdoLocationNotFoundError(NotFoundError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return f"Точка {self.org_unit_id} не найдена"


class EmptyEdoDocumentNumberError(EdoDomainError):
    def __str__(self) -> str:
        return "Укажите номер документа ЭДО"
