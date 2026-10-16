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
    image_url: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CategoryListItem:
    id: UUID
    name: str
    parent_id: UUID | None
    sort_order: int = 0


@dataclass(frozen=True, slots=True)
class NomenclaturePriceItem:
    price_list_id: UUID
    price_list_name: str
    is_active: bool
    value: int | None


@dataclass(frozen=True, slots=True)
class PriceListEntry:
    id: UUID
    name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class PriceListBindingItem:
    org_unit_id: UUID
    price_list_id: UUID


@dataclass(frozen=True, slots=True)
class PriceListPriceItem:
    nomenclature_id: UUID
    nomenclature_name: str
    sku: str
    value: int | None


@dataclass(frozen=True, slots=True)
class AssortmentItem:
    nomenclature_id: UUID
    name: str
    sku: str
    unit: UnitOfMeasurement
    value: int
    category_id: UUID | None = None
    category_name: str | None = None
    image_url: str | None = None
    description: str | None = None
