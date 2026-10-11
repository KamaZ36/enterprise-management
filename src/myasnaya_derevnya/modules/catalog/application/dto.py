from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)


@dataclass(frozen=True, slots=True)
class NomenclatureListItem:
    id: UUID
    sku: str
    name: str
    type: NomenclatureType
    unit: UnitOfMeasurement
    category_id: UUID
    category_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class CategoryListItem:
    id: UUID
    name: str
    parent_id: UUID | None
