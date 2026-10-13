from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.inventory.application.dto import (
    ReceiptDetail,
    ReceiptListItem,
    TransferDetail,
    TransferLineItem,
    TransferListItem,
    WarehouseListItem,
    WriteOffDetail,
    WriteOffListItem,
)
from myasnaya_derevnya.modules.inventory.application.interactors.balances.read import (
    BalanceListItem,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    WarehouseType,
)


class CreateWarehouseSchema(BaseModel):
    org_unit_id: UUID
    code: str
    name: str
    type: WarehouseType


class UpdateWarehouseSchema(BaseModel):
    name: str | None = None
    type: WarehouseType | None = None
    is_active: bool | None = None


class ReceiptLineSchema(BaseModel):
    nomenclature_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(default=Decimal(0), ge=0)
    lot_code: str | None = None
    expires_at: date | None = None


class CreateReceiptSchema(BaseModel):
    warehouse_id: UUID
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
    warehouse_id: UUID
    occurred_at: datetime
    lines: list[WriteOffLineSchema] = Field(min_length=1)
    reason: str | None = None
    comment: str | None = None


class WarehouseSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    code: str
    name: str
    type: WarehouseType
    is_active: bool

    @classmethod
    def from_dto(cls, warehouse: WarehouseListItem) -> WarehouseSchema:
        return cls(
            id=warehouse.id,
            org_unit_id=warehouse.org_unit_id,
            code=warehouse.code,
            name=warehouse.name,
            type=warehouse.type,
            is_active=warehouse.is_active,
        )


class BalanceSchema(BaseModel):
    warehouse_id: UUID
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
            warehouse_id=item.warehouse_id,
            nomenclature_id=item.nomenclature_id,
            nomenclature_name=item.nomenclature_name,
            quantity=item.quantity,
            average_unit_cost=item.average_unit_cost,
            total_value_kopecks=item.total_value_kopecks,
        )


class BalanceListSchema(BaseModel):
    items: list[BalanceSchema]
    total: int


class ReceiptListItemSchema(BaseModel):
    id: UUID
    warehouse_id: UUID
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
            warehouse_id=item.warehouse_id,
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
    warehouse_id: UUID
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
            warehouse_id=detail.warehouse_id,
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
    warehouse_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    reason: str | None
    line_count: int

    @classmethod
    def from_dto(cls, item: WriteOffListItem) -> WriteOffListItemSchema:
        return cls(
            id=item.id,
            warehouse_id=item.warehouse_id,
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
    warehouse_id: UUID
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
            warehouse_id=detail.warehouse_id,
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
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    occurred_at: datetime
    lines: list[TransferLineSchema] = Field(min_length=1)
    comment: str | None = None


class TransferListItemSchema(BaseModel):
    id: UUID
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    line_count: int

    @classmethod
    def from_dto(cls, item: TransferListItem) -> TransferListItemSchema:
        return cls(
            id=item.id,
            from_warehouse_id=item.from_warehouse_id,
            to_warehouse_id=item.to_warehouse_id,
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
    from_warehouse_id: UUID
    to_warehouse_id: UUID
    status: str
    occurred_at: datetime
    posted_at: datetime | None
    comment: str | None
    lines: list[TransferLineViewSchema]

    @classmethod
    def from_dto(cls, detail: TransferDetail) -> TransferDetailSchema:
        return cls(
            id=detail.id,
            from_warehouse_id=detail.from_warehouse_id,
            to_warehouse_id=detail.to_warehouse_id,
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
