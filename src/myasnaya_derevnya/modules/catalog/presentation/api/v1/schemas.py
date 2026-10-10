from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from myasnaya_derevnya.modules.catalog.application.dto import (
    CategoryListItem,
    NomenclatureListItem,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)

# NOMENCLATURE


class CreateNomenclatureSchema(BaseModel):
    sku: str
    name: str
    unit: UnitOfMeasurement
    type: NomenclatureType
    category_id: UUID


class NomenclatureSchema(BaseModel):
    id: UUID
    sku: str
    name: str
    type: NomenclatureType
    unit: UnitOfMeasurement
    category_id: UUID
    category_name: str

    @classmethod
    def from_dto(cls, item: NomenclatureListItem) -> NomenclatureSchema:
        return cls(
            id=item.id,
            sku=item.sku,
            name=item.name,
            type=item.type,
            unit=item.unit,
            category_id=item.category_id,
            category_name=item.category_name,
        )


class NomenclatureListSchema(BaseModel):
    items: list[NomenclatureSchema]
    total: int
    limit: int
    offset: int


# CATEGORY


class CreateCategorySchema(BaseModel):
    name: str
    parent_id: UUID | None


class CategorySchema(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None

    @classmethod
    def from_dto(cls, item: CategoryListItem) -> CategorySchema:
        return cls(id=item.id, name=item.name, parent_id=item.parent_id)


# PRICE LIST


class CreatePriceListSchema(BaseModel):
    name: str


# PRICE


class CreatePriceSchema(BaseModel):
    nomenclature_id: UUID
    price: Decimal
