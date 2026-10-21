from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from myasnaya_derevnya.modules.fiscal.application.dto import (
    CashRegisterBindingItem,
    CashRegisterDetail,
    CashRegisterListItem,
    StockLocationOption,
)


class CreateCashRegisterSchema(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    reg_number: str | None = Field(default=None, max_length=32)
    serial_number: str | None = Field(default=None, max_length=32)
    fiscal_place: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=128)
    fn_number: str | None = Field(default=None, max_length=32)
    ffd_version: str | None = Field(default=None, max_length=8)
    company_id: UUID | None = None
    registered_at: datetime | None = None
    attributes: dict | None = None


class UpdateCashRegisterSchema(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    reg_number: str | None = Field(default=None, max_length=32)
    serial_number: str | None = Field(default=None, max_length=32)
    fiscal_place: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=128)
    fn_number: str | None = Field(default=None, max_length=32)
    ffd_version: str | None = Field(default=None, max_length=8)
    company_id: UUID | None = None
    registered_at: datetime | None = None
    attributes: dict | None = None
    is_active: bool | None = None


class BindCashRegisterSchema(BaseModel):
    org_unit_id: UUID
    effective_from: datetime | None = None


class StockLocationOptionSchema(BaseModel):
    id: UUID
    name: str
    is_active: bool

    @classmethod
    def from_dto(cls, item: StockLocationOption) -> StockLocationOptionSchema:
        return cls(id=item.id, name=item.name, is_active=item.is_active)


class UnbindCashRegisterSchema(BaseModel):
    effective_to: datetime | None = None


class CashRegisterBindingSchema(BaseModel):
    id: UUID
    org_unit_id: UUID
    org_unit_name: str | None
    effective_from: datetime
    effective_to: datetime | None

    @classmethod
    def from_dto(cls, item: CashRegisterBindingItem) -> CashRegisterBindingSchema:
        return cls(
            id=item.id,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
            effective_from=item.effective_from,
            effective_to=item.effective_to,
        )


class CashRegisterSchema(BaseModel):
    id: UUID
    reg_number: str | None
    serial_number: str | None
    name: str
    fiscal_place: str | None
    model: str | None
    fn_number: str | None
    ffd_version: str | None
    company_id: UUID | None
    registered_at: datetime | None
    deregistered_at: datetime | None
    is_active: bool
    org_unit_id: UUID | None
    org_unit_name: str | None

    @classmethod
    def from_dto(cls, item: CashRegisterListItem) -> CashRegisterSchema:
        return cls(
            id=item.id,
            reg_number=item.reg_number,
            serial_number=item.serial_number,
            name=item.name,
            fiscal_place=item.fiscal_place,
            model=item.model,
            fn_number=item.fn_number,
            ffd_version=item.ffd_version,
            company_id=item.company_id,
            registered_at=item.registered_at,
            deregistered_at=item.deregistered_at,
            is_active=item.is_active,
            org_unit_id=item.org_unit_id,
            org_unit_name=item.org_unit_name,
        )


class CashRegisterDetailSchema(CashRegisterSchema):
    bindings: list[CashRegisterBindingSchema]

    @classmethod
    def from_detail(cls, item: CashRegisterDetail) -> CashRegisterDetailSchema:
        return cls(
            **CashRegisterSchema.from_dto(item).model_dump(),
            bindings=[
                CashRegisterBindingSchema.from_dto(binding)
                for binding in item.bindings
            ],
        )
