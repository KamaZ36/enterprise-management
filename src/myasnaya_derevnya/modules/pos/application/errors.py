from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


@dataclass(slots=True, eq=False)
class PosSourceNotFoundError(NotFoundError):
    source_id: UUID

    def __str__(self) -> str:
        return f"Источник продаж DoKa {self.source_id} не найден."


@dataclass(slots=True, eq=False)
class PosSourceByDokaOrgIdNotFoundError(NotFoundError):
    doka_org_id: str

    def __str__(self) -> str:
        return f"Источник DoKa с ИД {self.doka_org_id} не зарегистрирован."


@dataclass(slots=True, eq=False)
class PosSourceAlreadyExistsError(ConflictError):
    doka_org_id: str

    def __str__(self) -> str:
        return f"Источник DoKa с ИД {self.doka_org_id} уже существует."


@dataclass(slots=True, eq=False)
class PosAgentNotFoundError(NotFoundError):
    agent_id: UUID

    def __str__(self) -> str:
        return f"Агент сбора продаж {self.agent_id} не найден."


@dataclass(slots=True, eq=False)
class PosReceiptNotFoundError(NotFoundError):
    receipt_id: UUID

    def __str__(self) -> str:
        return f"Чек DoKa {self.receipt_id} не найден."


@dataclass(slots=True, eq=False)
class PosProductMappingNotFoundError(NotFoundError):
    mapping_id: UUID

    def __str__(self) -> str:
        return f"Сопоставление товара DoKa {self.mapping_id} не найдено."


@dataclass(slots=True, eq=False)
class NomenclatureForMappingNotFoundError(NotFoundError):
    nomenclature_id: UUID

    def __str__(self) -> str:
        return f"Номенклатура {self.nomenclature_id} не найдена."


class InvalidAgentCredentialsError(UnauthorizedError):
    def __str__(self) -> str:
        return "Неверный или отозванный ключ агента."


class MissingAgentHeadersError(UnauthorizedError):
    def __str__(self) -> str:
        return "Не передан заголовок Authorization или X-Install-Id."


@dataclass(slots=True, eq=False)
class PosSourceInactiveError(ForbiddenError):
    doka_org_id: str

    def __str__(self) -> str:
        return f"Источник продаж DoKa {self.doka_org_id} отключён."


@dataclass(slots=True, eq=False)
class PosLocationNotFoundError(ValidationError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return (
            f"Подразделение {self.org_unit_id} не найдено "
            "или не является складской локацией."
        )


class EmptyReceiptsBatchError(ValidationError):
    def __str__(self) -> str:
        return "В запросе нет ни одного чека."


class TooManyReceiptsError(ValidationError):
    def __str__(self) -> str:
        return "За один запрос можно передать не более 100 чеков."


@dataclass(slots=True, eq=False)
class AgentSourceMismatchError(ForbiddenError):
    doka_org_id: str

    def __str__(self) -> str:
        return (
            f"Ключ агента выдан другому источнику DoKa, "
            f"а запрос прислан от {self.doka_org_id}."
        )
