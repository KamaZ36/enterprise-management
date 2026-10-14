from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ConflictError, NotFoundError


@dataclass(slots=True, eq=False)
class NomenclatureNotFound(NotFoundError):
    nomenclature_id: UUID

    def __str__(self) -> str:
        return f"Номенклатура {self.nomenclature_id} не найдена."


@dataclass(slots=True, eq=False)
class CategoryNotFound(NotFoundError):
    category_id: UUID

    def __str__(self) -> str:
        return f"Категория {self.category_id} не найдена."


@dataclass(slots=True, eq=False)
class CategoryAlreadyExists(ConflictError):
    category_name: str

    def __str__(self) -> str:
        return f"Категория '{self.category_name}' уже существует."


@dataclass(slots=True, eq=False)
class PriceListAlreadyExists(ConflictError):
    price_list_name: str

    def __str__(self) -> str:
        return f"Прайс-Лист '{self.price_list_name}' уже существует."


@dataclass(slots=True, eq=False)
class PriceListNotFound(NotFoundError):
    price_list_id: UUID

    def __str__(self) -> str:
        return f"Прайс-лист {self.price_list_id} не найден."
