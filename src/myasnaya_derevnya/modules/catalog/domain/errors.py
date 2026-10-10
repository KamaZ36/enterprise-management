from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import DomainError


@dataclass(slots=True, eq=False)
class CatalogDomainError(DomainError):
    """Базовое исключение для всех нарушений бизнес-правил в модуле Catalog."""

    def __str__(self) -> str:
        return "Ошибка модуля Catalog"


# НОМЕНКЛАТУРА И КАТЕГОРИИ


@dataclass(slots=True, eq=False)
class EmptyNameError(CatalogDomainError):
    def __str__(self) -> str:
        return "Название не может быть пустым"


@dataclass(slots=True, eq=False)
class EmptySkuError(CatalogDomainError):
    def __str__(self) -> str:
        return "Артикул (SKU) не может быть пустым"


@dataclass(slots=True, eq=False)
class InvalidGtinError(CatalogDomainError):
    gtin: str

    def __str__(self) -> str:
        return f"Некорректный формат штрихкода GTIN: '{self.gtin}'. Должен содержать 8, 13 или 14 цифр."


@dataclass(slots=True, eq=False)
class CategoryCannotBeParentOfItselfError(CatalogDomainError):
    category_id: UUID

    def __str__(self) -> str:
        return f"Циклическая зависимость: категория {self.category_id} не может быть родительской для самой себя"


# ЦЕНЫ


@dataclass(slots=True, eq=False)
class NegativePriceValueError(CatalogDomainError):
    def __str__(self) -> str:
        return "Цена не может быть отрицательной"
