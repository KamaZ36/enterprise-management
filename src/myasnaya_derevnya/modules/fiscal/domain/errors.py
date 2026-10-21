from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import DomainError


class FiscalDomainError(DomainError):
    def __str__(self) -> str:
        return "Ошибка правил кассы"


class TimezoneRequiredError(FiscalDomainError):
    def __str__(self) -> str:
        return "Время должно быть с указанием часового пояса."


class InvalidRegNumberError(FiscalDomainError):
    def __str__(self) -> str:
        return "РНМ должен состоять из 16 цифр."


@dataclass(slots=True, eq=False)
class RegNumberRequiredError(FiscalDomainError):
    cash_register_id: UUID

    def __str__(self) -> str:
        return (
            f"Кассу {self.cash_register_id} нельзя привязать: "
            "сначала укажите РНМ."
        )


@dataclass(slots=True, eq=False)
class InactiveCashRegisterError(FiscalDomainError):
    cash_register_id: UUID

    def __str__(self) -> str:
        return f"Касса {self.cash_register_id} снята с учёта."


@dataclass(slots=True, eq=False)
class AlreadyBoundError(FiscalDomainError):
    cash_register_id: UUID
    org_unit_id: UUID

    def __str__(self) -> str:
        return (
            f"Касса {self.cash_register_id} уже привязана "
            f"к подразделению {self.org_unit_id}."
        )


@dataclass(slots=True, eq=False)
class BindingConflictError(FiscalDomainError):
    cash_register_id: UUID

    def __str__(self) -> str:
        return (
            f"У кассы {self.cash_register_id} уже есть привязка, "
            "начавшаяся позже указанной даты."
        )


@dataclass(slots=True, eq=False)
class NoOpenBindingError(FiscalDomainError):
    cash_register_id: UUID

    def __str__(self) -> str:
        return f"У кассы {self.cash_register_id} нет открытой привязки."


class InvalidBindingPeriodError(FiscalDomainError):
    def __str__(self) -> str:
        return "Дата окончания привязки должна быть позже даты начала."


@dataclass(slots=True, eq=False)
class BindingTargetNotStockLocationError(FiscalDomainError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return (
            f"Подразделение {self.org_unit_id} не является складской локацией "
            "и не может быть привязано к кассе."
        )


@dataclass(slots=True, eq=False)
class BindingTargetInactiveError(FiscalDomainError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return f"Подразделение {self.org_unit_id} закрыто."
