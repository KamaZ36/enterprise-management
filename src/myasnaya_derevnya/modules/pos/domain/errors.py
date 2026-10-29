from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import DomainError


class PosDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка правил сбора продаж"


class InvalidDokaGuidError(PosDomainError):
    def __str__(self) -> str:
        return "Идентификатор DoKa должен состоять из 32 или 44 hex-символов."


class InvalidDokaOrgIdError(PosDomainError):
    def __str__(self) -> str:
        return "Идентификатор организации DoKa должен состоять из цифр."


class InvalidPosQuantityError(PosDomainError):
    def __str__(self) -> str:
        return "Количество в чеке DoKa должно быть больше нуля."


class InvalidPosAmountError(PosDomainError):
    def __str__(self) -> str:
        return "Сумма в чеке DoKa не может быть отрицательной."


@dataclass(slots=True, eq=False)
class EmptyPosTextError(PosDomainError):
    field: str

    def __str__(self) -> str:
        return f"Поле «{self.field}» не может быть пустым."


class InvalidUnitFactorError(PosDomainError):
    def __str__(self) -> str:
        return "Коэффициент пересчёта должен быть больше нуля."


class TimezoneRequiredError(PosDomainError):
    def __str__(self) -> str:
        return "Время чека DoKa должно быть с указанием часового пояса."


@dataclass(slots=True, eq=False)
class ReceiptNotPostableError(PosDomainError):
    receipt_id: UUID
    reason: str

    def __str__(self) -> str:
        return f"Чек DoKa {self.receipt_id} нельзя провести: {self.reason}"


@dataclass(slots=True, eq=False)
class ReplyNotSupportedError(PosDomainError):
    receipt_id: UUID

    def __str__(self) -> str:
        return (
            f"Чек DoKa {self.receipt_id} является возвратом; "
            "автоматическое проведение возвратов пока не поддерживается."
        )
