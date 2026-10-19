from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.inventory.application.dto import (
    BalanceListItem,
    InventoryCountDetail,
    InventoryCountLineItem,
    InventoryCountListItem,
    LocationListItem,
    LotBalanceListItem,
    MovementListItem,
    ReceiptDetail,
    ReceiptListItem,
    TransferDetail,
    TransferLineItem,
    TransferListItem,
    WriteOffDetail,
    WriteOffListItem,
)


class LocationSchema(BaseModel):
    id: UUID
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, location: LocationListItem) -> LocationSchema:
        return cls(
            id=location.id,
            name=location.name,
            is_active=location.is_active,
        )


class ReceiptLineSchema(BaseModel):
    nomenclature_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal(0), ge=0)
    lot_code: str | None = None
    expires_at: date | None = None


class CreateReceiptSchema(BaseModel):
    org_unit_id: UUID
    occurred_at: datetime
    lines: list[ReceiptLineSchema] = Field(min_length=1)
    supplier_name: str | None = None
    supplier_document_number: str | None = None
    comment: str | None = None


class WriteOffLineSchema(BaseModel):
    nomenclature_id: UUID
    quantity: Decimal = Field(gt=0)
    lot_code: str | None = None


class CreateWriteOffSchema(BaseModel):
    org_unit_id: UUID
    occurred_at: datetime
    lines: list[WriteOffLineSchema] = Field(min_length=1)
    reason: str | None = None
    comment: str | None = None


class BalanceSchema(BaseModel):
    org_unit_id: UUID
    nomenclature_id: UUID
    nomenclature_name: str | None = None
    quantity: Decimal
    average_unit_cost: Decimal | None = Field(
        default=None,
        description="Средняя себестоимость единицы, рубли. null — нет права видеть стоимость",
    )
    total_value_kopecks: int | None = Field(
        default=None,
        description="Стоимость остатка в копейках. null — нет права видеть стоимость",
    )

    @classmethod
    def from_dto(cls, item: BalanceListItem) -> BalanceSchema:
        return cls(
            org_unit_id=item.org_unit_id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            average_unit_cost=item.average_unit_cost,
            total_value_kopecks=item.total_value_kopecks,
        )


class BalanceListSchema(BaseModel):
    items: list[BalanceSchema]
    total: int
    limit: int
    offset: int


class LotBalanceSchema(BaseModel):
    org_unit_id: UUID
    nomenclature_id: UUID
    nomenclature_name: str | None = None
    lot_id: UUID
    lot_code: str
    quantity: Decimal
    expires_at: date | None = None
    produced_at: date | None = None
    supplier_name: str | None = None
    unit_cost: Decimal | None = Field(
        default=None,
        description="Себестоимость единицы по партии, рубли. null — нет права видеть стоимость",
    )
    total_value_kopecks: int | None = Field(
        default=None,
        description="Стоимость партии в копейках. null — нет права видеть стоимость",
    )

    @classmethod
    def from_dto(cls, item: LotBalanceListItem) -> LotBalanceSchema:
        return cls(
            org_unit_id=item.org_unit_id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            lot_id=item.lot_id,
            lot_code=item.lot_code,
            quantity=item.quantity,
            expires_at=item.expires_at,
            produced_at=item.produced_at,
            supplier_name=item.supplier_name,
            unit_cost=item.unit_cost,
            total_value_kopecks=item.total_value_kopecks,
        )


class LotBalanceListSchema(BaseModel):
    items: list[LotBalanceSchema]
    total: int
    limit: int
    offset: int


class MovementItemSchema(BaseModel):
    id: UUID
    occurred_at: datetime
    org_unit_id: UUID
    location_name: str | None = None
    nomenclature_id: UUID
    nomenclature_name: str | None = None
    lot_id: UUID | None = None
    lot_code: str | None = None
    movement_type: str
    quantity: Decimal
    total_cost_kopecks: int | None = Field(
        default=None,
        description="Сумма движения в копейках. null — нет права видеть стоимость",
    )

    @classmethod
    def from_dto(cls, item: MovementListItem) -> MovementItemSchema:
        return cls(
            id=item.id,
            occurred_at=item.occurred_at,
            org_unit_id=item.org_unit_id,
            location_name=item.location_name,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            lot_id=item.lot_id,
            lot_code=item.lot_code,
            movement_type=item.movement_type,
            quantity=item.quantity,
            total_cost_kopecks=item.total_cost_kopecks,
        )


class MovementListSchema(BaseModel):
    items: list[MovementItemSchema]
    total: int
    limit: int
    offset: int


class ReceiptListItemSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    supplier_name: str | None
    supplier_document_number: str | None
    line_count: int
    total_kopecks: int

    @classmethod
    def from_dto(cls, item: ReceiptListItem) -> ReceiptListItemSchema:
        return cls(
            id=item.id,
            org_unit_id=item.org_unit_id,
            status=item.status,
            occurred_at=item.occurred_at,
            posted_at=item.posted_at,
            supplier_name=item.supplier_name,
            supplier_document_number=item.supplier_document_number,
            line_count=item.line_count,
            total_kopecks=item.total_kopecks,
        )


class ReceiptLineViewSchema(BaseModel):
    id: UUID
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    unit_cost: Decimal
    total_kopecks: int
    lot_code: str | None
    expires_at: date | None

    @classmethod
    def from_dto(cls, item) -> ReceiptLineViewSchema:
        return cls(
            id=item.id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            total_kopecks=item.total_kopecks,
            lot_code=item.lot_code,
            expires_at=item.expires_at,
        )


class ReceiptListSchema(BaseModel):
    items: list[ReceiptListItemSchema]
    total: int
    limit: int
    offset: int


class ReceiptDetailSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    supplier_name: str | None
    supplier_document_number: str | None
    comment: str | None
    lines: list[ReceiptLineViewSchema]

    @classmethod
    def from_dto(cls, detail: ReceiptDetail) -> ReceiptDetailSchema:
        return cls(
            id=detail.id,
            org_unit_id=detail.org_unit_id,
            status=detail.status,
            occurred_at=detail.occurred_at,
            posted_at=detail.posted_at,
            supplier_name=detail.supplier_name,
            supplier_document_number=detail.supplier_document_number,
            comment=detail.comment,
            lines=[ReceiptLineViewSchema.from_dto(line) for line in detail.lines],
        )


class WriteOffListItemSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    reason: str | None
    line_count: int

    @classmethod
    def from_dto(cls, item: WriteOffListItem) -> WriteOffListItemSchema:
        return cls(
            id=item.id,
            org_unit_id=item.org_unit_id,
            status=item.status,
            occurred_at=item.occurred_at,
            posted_at=item.posted_at,
            reason=item.reason,
            line_count=item.line_count,
        )


class WriteOffLineViewSchema(BaseModel):
    id: UUID
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    lot_code: str | None

    @classmethod
    def from_dto(cls, item) -> WriteOffLineViewSchema:
        return cls(
            id=item.id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            lot_code=item.lot_code,
        )


class WriteOffListSchema(BaseModel):
    items: list[WriteOffListItemSchema]
    total: int
    limit: int
    offset: int


class WriteOffDetailSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    reason: str | None
    comment: str | None
    lines: list[WriteOffLineViewSchema]

    @classmethod
    def from_dto(cls, detail: WriteOffDetail) -> WriteOffDetailSchema:
        return cls(
            id=detail.id,
            org_unit_id=detail.org_unit_id,
            status=detail.status,
            occurred_at=detail.occurred_at,
            posted_at=detail.posted_at,
            reason=detail.reason,
            comment=detail.comment,
            lines=[WriteOffLineViewSchema.from_dto(line) for line in detail.lines],
        )


class TransferLineSchema(BaseModel):
    nomenclature_id: UUID
    quantity: Decimal = Field(gt=0)
    lot_code: str | None = None


class CreateTransferSchema(BaseModel):
    from_org_unit_id: UUID
    to_org_unit_id: UUID
    occurred_at: datetime
    lines: list[TransferLineSchema] = Field(min_length=1)
    comment: str | None = None


class TransferListItemSchema(BaseModel):
    id: UUID
    from_org_unit_id: UUID
    to_org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    line_count: int

    @classmethod
    def from_dto(cls, item: TransferListItem) -> TransferListItemSchema:
        return cls(
            id=item.id,
            from_org_unit_id=item.from_org_unit_id,
            to_org_unit_id=item.to_org_unit_id,
            status=item.status,
            occurred_at=item.occurred_at,
            posted_at=item.posted_at,
            comment=item.comment,
            line_count=item.line_count,
        )


class TransferLineViewSchema(BaseModel):
    id: UUID
    nomenclature_id: UUID
    nomenclature_name: str | None
    quantity: Decimal
    lot_code: str | None

    @classmethod
    def from_dto(cls, item: TransferLineItem) -> TransferLineViewSchema:
        return cls(
            id=item.id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            lot_code=item.lot_code,
        )


class TransferListSchema(BaseModel):
    items: list[TransferListItemSchema]
    total: int
    limit: int
    offset: int


class TransferDetailSchema(BaseModel):
    id: UUID
    from_org_unit_id: UUID
    to_org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    lines: list[TransferLineViewSchema]

    @classmethod
    def from_dto(cls, detail: TransferDetail) -> TransferDetailSchema:
        return cls(
            id=detail.id,
            from_org_unit_id=detail.from_org_unit_id,
            to_org_unit_id=detail.to_org_unit_id,
            status=detail.status,
            occurred_at=detail.occurred_at,
            posted_at=detail.posted_at,
            comment=detail.comment,
            lines=[TransferLineViewSchema.from_dto(line) for line in detail.lines],
        )


class UpdateTransferSchema(BaseModel):
    occurred_at: datetime
    lines: list[TransferLineSchema] = Field(min_length=1)
    comment: str | None = None


class InventoryCountLineSchema(BaseModel):
    nomenclature_id: UUID
    counted_quantity: Decimal = Field(ge=0)
    lot_code: str | None = None


class CreateInventoryCountSchema(BaseModel):
    org_unit_id: UUID
    occurred_at: datetime
    lines: list[InventoryCountLineSchema] = Field(min_length=1)
    comment: str | None = None


class UpdateInventoryCountSchema(BaseModel):
    occurred_at: datetime
    lines: list[InventoryCountLineSchema] = Field(min_length=1)
    comment: str | None = None


class InventoryCountListItemSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    line_count: int

    @classmethod
    def from_dto(
        cls, item: InventoryCountListItem
    ) -> InventoryCountListItemSchema:
        return cls(
            id=item.id,
            org_unit_id=item.org_unit_id,
            status=item.status,
            occurred_at=item.occurred_at,
            posted_at=item.posted_at,
            comment=item.comment,
            line_count=item.line_count,
        )


class InventoryCountLineViewSchema(BaseModel):
    id: UUID
    nomenclature_id: UUID
    nomenclature_name: str | None
    counted_quantity: Decimal
    lot_code: str | None

    @classmethod
    def from_dto(cls, item: InventoryCountLineItem) -> InventoryCountLineViewSchema:
        return cls(
            id=item.id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            counted_quantity=item.counted_quantity,
            lot_code=item.lot_code,
        )


class InventoryCountListSchema(BaseModel):
    items: list[InventoryCountListItemSchema]
    total: int
    limit: int
    offset: int


class InventoryCountDetailSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    lines: list[InventoryCountLineViewSchema]

    @classmethod
    def from_dto(cls, detail: InventoryCountDetail) -> InventoryCountDetailSchema:
        return cls(
            id=detail.id,
            org_unit_id=detail.org_unit_id,
            status=detail.status,
            occurred_at=detail.occurred_at,
            posted_at=detail.posted_at,
            comment=detail.comment,
            lines=[
                InventoryCountLineViewSchema.from_dto(line) for line in detail.lines
            ],
        )
