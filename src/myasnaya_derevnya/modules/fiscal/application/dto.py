from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CashRegisterListItem:
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
    org_unit_id: UUID | None = None
    org_unit_name: str | None = None


@dataclass(frozen=True, slots=True)
class CashRegisterBindingItem:
    id: UUID
    org_unit_id: UUID
    effective_from: datetime
    effective_to: datetime | None
    org_unit_name: str | None = None


@dataclass(frozen=True, slots=True)
class CashRegisterDetail(CashRegisterListItem):
    bindings: tuple[CashRegisterBindingItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class StockLocationOption:
    id: UUID
    name: str
    is_active: bool
