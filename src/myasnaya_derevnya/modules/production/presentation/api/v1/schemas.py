from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.production.application.dto import (
    ProductionOrderDetail,
    ProductionOrderLineItem,
    ProductionOrderListItem,
    TechCardDetail,
    TechCardLineItem,
    TechCardListItem,
)
from myasnaya_derevnya.modules.production.domain.value_objects.loss_kind import (
    LossKind,
)
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.domain.value_objects.spec_line_role import (
    OutputKind,
    SpecLineRole,
)
from myasnaya_derevnya.modules.production.domain.value_objects.tech_card_basis import (
    TechCardBasis,
)


class TechCardLineSchema(BaseModel):
    id: UUID
    role: SpecLineRole
    quantity: Decimal
    nomenclature_id: UUID | None = None
    nomenclature_name: str | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost_coefficient: Decimal | None = None

    @classmethod
    def from_dto(cls, item: TechCardLineItem) -> TechCardLineSchema:
        return cls(
            id=item.id,
            role=item.role,
            quantity=item.quantity,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            loss_kind=item.loss_kind,
            output_kind=item.output_kind,
            cost_coefficient=item.cost_coefficient,
        )


class TechCardListItemSchema(BaseModel):
    id: UUID
    code: str
    version: int
    name: str
    basis: TechCardBasis
    created_at: datetime
    line_count: int
    valid_from: date | None = None
    comment: str | None = None

    @classmethod
    def from_dto(cls, item: TechCardListItem) -> TechCardListItemSchema:
        return cls(
            id=item.id,
            code=item.code,
            version=item.version,
            name=item.name,
            basis=item.basis,
            created_at=item.created_at,
            line_count=item.line_count,
            valid_from=item.valid_from,
            comment=item.comment,
        )


class TechCardListSchema(BaseModel):
    items: list[TechCardListItemSchema]
    total: int


class TechCardDetailSchema(BaseModel):
    id: UUID
    code: str
    version: int
    name: str
    basis: TechCardBasis
    created_at: datetime
    lines: list[TechCardLineSchema]
    valid_from: date | None = None
    comment: str | None = None

    @classmethod
    def from_dto(cls, item: TechCardDetail) -> TechCardDetailSchema:
        return cls(
            id=item.id,
            code=item.code,
            version=item.version,
            name=item.name,
            basis=item.basis,
            created_at=item.created_at,
            lines=[TechCardLineSchema.from_dto(line) for line in item.lines],
            valid_from=item.valid_from,
            comment=item.comment,
        )


class TechCardLineInputSchema(BaseModel):
    role: SpecLineRole
    quantity: Decimal = Field(gt=0)
    nomenclature_id: UUID | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost_coefficient: Decimal | None = Field(default=None, gt=0)


class CreateTechCardSchema(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    basis: TechCardBasis
    lines: list[TechCardLineInputSchema] = Field(min_length=1)
    valid_from: date | None = None
    comment: str | None = None


class ProductionOrderLineSchema(BaseModel):
    id: UUID
    role: SpecLineRole
    planned_quantity: Decimal
    actual_quantity: Decimal
    nomenclature_id: UUID | None = None
    nomenclature_name: str | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost: int | None = None

    @classmethod
    def from_dto(cls, item: ProductionOrderLineItem) -> ProductionOrderLineSchema:
        return cls(
            id=item.id,
            role=item.role,
            planned_quantity=item.planned_quantity,
            actual_quantity=item.actual_quantity,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            loss_kind=item.loss_kind,
            output_kind=item.output_kind,
            cost=item.cost,
        )


class ProductionOrderListItemSchema(BaseModel):
    id: UUID
    warehouse_id: UUID
    tech_card_id: UUID
    tech_card_code: str
    tech_card_version: int
    status: ProductionOrderStatus
    occurred_at: datetime
    batch_count: Decimal
    created_at: datetime
    posted_at: datetime | None = None
    warehouse_name: str | None = None

    @classmethod
    def from_dto(
        cls, item: ProductionOrderListItem
    ) -> ProductionOrderListItemSchema:
        return cls(
            id=item.id,
            warehouse_id=item.warehouse_id,
            tech_card_id=item.tech_card_id,
            tech_card_code=item.tech_card_code,
            tech_card_version=item.tech_card_version,
            status=item.status,
            occurred_at=item.occurred_at,
            batch_count=item.batch_count,
            created_at=item.created_at,
            posted_at=item.posted_at,
            warehouse_name=item.warehouse_name,
        )


class ProductionOrderListSchema(BaseModel):
    items: list[ProductionOrderListItemSchema]
    total: int


class ProductionOrderDetailSchema(BaseModel):
    id: UUID
    warehouse_id: UUID
    tech_card_id: UUID
    tech_card_code: str
    tech_card_version: int
    status: ProductionOrderStatus
    occurred_at: datetime
    batch_count: Decimal
    created_at: datetime
    lines: list[ProductionOrderLineSchema]
    comment: str | None = None
    posted_at: datetime | None = None
    warehouse_name: str | None = None

    @classmethod
    def from_dto(
        cls, item: ProductionOrderDetail
    ) -> ProductionOrderDetailSchema:
        return cls(
            id=item.id,
            warehouse_id=item.warehouse_id,
            tech_card_id=item.tech_card_id,
            tech_card_code=item.tech_card_code,
            tech_card_version=item.tech_card_version,
            status=item.status,
            occurred_at=item.occurred_at,
            batch_count=item.batch_count,
            created_at=item.created_at,
            lines=[
                ProductionOrderLineSchema.from_dto(line) for line in item.lines
            ],
            comment=item.comment,
            posted_at=item.posted_at,
            warehouse_name=item.warehouse_name,
        )


class CreateProductionOrderSchema(BaseModel):
    warehouse_id: UUID
    tech_card_id: UUID
    batch_count: Decimal = Field(gt=0)
    occurred_at: datetime
    comment: str | None = None


class ProductionOrderActualSchema(BaseModel):
    line_id: UUID
    quantity: Decimal = Field(ge=0)


class UpdateProductionOrderSchema(BaseModel):
    actuals: list[ProductionOrderActualSchema] = Field(min_length=1)


class CreatedProductionSchema(BaseModel):
    id: UUID
