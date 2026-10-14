from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.catalog.application.dto import (
    AssortmentItem,
    CategoryListItem,
    NomenclatureListItem,
)
from myasnaya_derevnya.modules.catalog.domain.entities.nomenclature import (
    NomenclatureType,
    UnitOfMeasurement,
)


class CreateNomenclatureSchema(BaseModel):
    sku: str
    name: str
    unit: UnitOfMeasurement
    type: NomenclatureType
    category_id: UUID
    image_url: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=1024)


class NomenclatureSchema(BaseModel):
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
            is_active=item.is_active,
            image_url=item.image_url,
            description=item.description,
        )


class NomenclatureListSchema(BaseModel):
    items: list[NomenclatureSchema]
    total: int
    limit: int
    offset: int


class UploadedImageSchema(BaseModel):
    url: str
    width: int
    height: int
    size_bytes: int


class UpdateCategorySchema(BaseModel):
    name: str | None = Field(default=None, min_length=1)

    sort_order: int | None = None


class UpdateNomenclatureSchema(BaseModel):
    name: str | None = None
    category_id: UUID | None = None
    unit: UnitOfMeasurement | None = None
    type: NomenclatureType | None = None
    is_active: bool | None = None
    image_url: str | None = Field(default=None, max_length=512)
    description: str | None = Field(default=None, max_length=1024)


class CreateCategorySchema(BaseModel):
    name: str
    parent_id: UUID | None
    sort_order: int = 0


class CategorySchema(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None
    sort_order: int = 0

    @classmethod
    def from_dto(cls, item: CategoryListItem) -> CategorySchema:
        return cls(
            id=item.id,
            name=item.name,
            parent_id=item.parent_id,
            sort_order=item.sort_order,
        )


class CreatePriceListSchema(BaseModel):
    name: str


class CreatePriceSchema(BaseModel):
    nomenclature_id: UUID
    price: Decimal


class BindPriceListSchema(BaseModel):
    price_list_id: UUID


class PriceListBindingSchema(BaseModel):
    org_unit_id: UUID
    price_list_id: UUID
    price_list_name: str | None = None


class NomenclaturePriceSchema(BaseModel):
    price_list_id: UUID
    price_list_name: str
    is_active: bool
    value: int | None

    @classmethod
    def from_dto(cls, item) -> NomenclaturePriceSchema:
        return cls(
            price_list_id=item.price_list_id,
            price_list_name=item.price_list_name,
            is_active=item.is_active,
            value=item.value,
        )


class NomenclaturePriceListSchema(BaseModel):
    items: list[NomenclaturePriceSchema]


class PriceListEntrySchema(BaseModel):
    id: UUID
    name: str
    is_active: bool


class PriceListEntryListSchema(BaseModel):
    items: list[PriceListEntrySchema]


class PriceListPriceSchema(BaseModel):
    nomenclature_id: UUID
    nomenclature_name: str
    sku: str
    value: int | None


class PriceListPriceListSchema(BaseModel):
    items: list[PriceListPriceSchema]
    total: int


class AssortmentItemSchema(BaseModel):
    nomenclature_id: UUID
    name: str
    sku: str
    unit: UnitOfMeasurement
    value: int
    category_id: UUID | None = None
    category_name: str | None = None
    image_url: str | None = None
    description: str | None = None

    @classmethod
    def from_dto(cls, item: AssortmentItem) -> AssortmentItemSchema:
        return cls(
            nomenclature_id=item.nomenclature_id,
            name=item.name,
            sku=item.sku,
            unit=item.unit,
            value=item.value,
            category_id=item.category_id,
            category_name=item.category_name,
            image_url=item.image_url,
            description=item.description,
        )


class AssortmentListSchema(BaseModel):
    items: list[AssortmentItemSchema]
