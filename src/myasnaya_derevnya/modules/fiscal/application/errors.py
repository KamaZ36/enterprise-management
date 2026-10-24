from dataclasses import dataclass
from datetime import date
from uuid import UUID

from myasnaya_derevnya.core.errors import AppError, NotFoundError, ValidationError


@dataclass(slots=True, eq=False)
class CashRegisterNotFound(NotFoundError):
    cash_register_id: UUID

    def __str__(self) -> str:
        return f"Касса {self.cash_register_id} не найдена."


@dataclass(slots=True, eq=False)
class OfdReceiptNotFound(NotFoundError):
    receipt_id: UUID

    def __str__(self) -> str:
        return f"Чек ОФД {self.receipt_id} не найден."


@dataclass(slots=True, eq=False)
class OfdReceiptLineNotFound(NotFoundError):
    line_id: UUID

    def __str__(self) -> str:
        return f"Строка чека ОФД {self.line_id} не найдена."


@dataclass(slots=True, eq=False)
class CashRegisterByRegNumberNotFound(NotFoundError):
    reg_number: str

    def __str__(self) -> str:
        return f"Касса с РНМ {self.reg_number} не найдена."


@dataclass(slots=True, eq=False)
class NomenclatureForMappingNotFound(NotFoundError):
    nomenclature_id: UUID

    def __str__(self) -> str:
        return f"Номенклатура {self.nomenclature_id} не найдена."


class OfdNotConfiguredError(ValidationError):
    def __str__(self) -> str:
        return (
            "Интеграция с ОФД не настроена: задайте OFD_API_TOKEN и OFD_INN."
        )


class InvalidOfdPeriodError(ValidationError):
    def __str__(self) -> str:
        return "Период выгрузки ОФД должен быть от 1 до 31 дня."


@dataclass(slots=True, eq=False)
class OfdPeriodBeforeCutoverError(ValidationError):
    cutover_date: date

    def __str__(self) -> str:
        return (
            "Нельзя загружать чеки ОФД раньше даты перехода "
            f"{self.cutover_date:%d.%m.%Y}."
        )


@dataclass(slots=True, eq=False)
class OfdApiError(AppError):
    message: str

    def __str__(self) -> str:
        return f"Ошибка ОФД: {self.message}"
