from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

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


# CATEGORY


class CreateCategorySchema(BaseModel):
    name: str
    parent_id: UUID | None


# PRICE LIST


class CreatePriceListSchema(BaseModel):
    name: str


# PRICE


class CreatePriceSchema(BaseModel):
    nomenclature_id: UUID
    price: Decimal
