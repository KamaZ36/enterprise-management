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


@dataclass(slots=True, eq=False)
class StopListLocationNotFound(NotFoundError):
    org_unit_id: UUID

    def __str__(self) -> str:
        return f"Точка {self.org_unit_id} не найдена или не хранит запасы."


@dataclass(slots=True, eq=False)
class StopListItemNotFound(NotFoundError):
    org_unit_id: UUID
    nomenclature_id: UUID

    def __str__(self) -> str:
        return (
            f"Номенклатура {self.nomenclature_id} не найдена "
            f"в стоп-листе точки {self.org_unit_id}."
        )
