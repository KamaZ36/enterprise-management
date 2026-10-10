from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.inventory.application.interactors.read_balances import (
    BalanceView,
)
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import (
    Warehouse,
    WarehouseType,
)


class CreateWarehouseSchema(BaseModel):
    org_unit_id: UUID
    code: str
    name: str
    type: WarehouseType


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
    def from_entity(cls, warehouse: Warehouse) -> WarehouseSchema:
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
    def from_view(cls, view: BalanceView) -> BalanceSchema:
        balance = view.balance

        return cls(
            warehouse_id=balance.warehouse_id,
            nomenclature_id=balance.nomenclature_id,
            quantity=balance.quantity,
            average_unit_cost=(
                balance.average_unit_cost if view.cost_visible else None
            ),
            total_value_kopecks=(
                balance.total_value.kopecks if view.cost_visible else None
            ),
        )


class BalanceListSchema(BaseModel):
    items: list[BalanceSchema]
    total: int
