from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)


@dataclass(frozen=True, slots=True)
class NomenclatureListItem:
    """Строка списка номенклатуры: плоские данные для интерфейса."""

    id: UUID
    sku: str
    name: str
    type: NomenclatureType
    unit: UnitOfMeasurement
    category_id: UUID
    category_name: str


@dataclass(frozen=True, slots=True)
class CategoryListItem:
    """Строка справочника категорий: список отдаётся целиком."""

    id: UUID
    name: str
    parent_id: UUID | None
