from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

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


@dataclass(frozen=True, slots=True)
class TechCardLineItem:
    id: UUID
    role: SpecLineRole
    nomenclature_id: UUID | None
    quantity: Decimal
    nomenclature_name: str | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost_coefficient: Decimal | None = None


@dataclass(frozen=True, slots=True)
class TechCardListItem:
    id: UUID
    code: str
    version: int
    name: str
    basis: TechCardBasis
    created_at: datetime
    line_count: int
    valid_from: date | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class TechCardDetail:
    id: UUID
    code: str
    version: int
    name: str
    basis: TechCardBasis
    created_at: datetime
    lines: list[TechCardLineItem]
    valid_from: date | None = None
    comment: str | None = None


@dataclass(frozen=True, slots=True)
class TechCardPage:
    items: list[TechCardListItem]
    total: int


@dataclass(frozen=True, slots=True)
class ProductionOrderLineItem:
    id: UUID
    role: SpecLineRole
    planned_quantity: Decimal
    actual_quantity: Decimal
    nomenclature_id: UUID | None = None
    nomenclature_name: str | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost: int | None = None


@dataclass(frozen=True, slots=True)
class ProductionOrderListItem:
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


@dataclass(frozen=True, slots=True)
class ProductionOrderDetail:
    id: UUID
    warehouse_id: UUID
    tech_card_id: UUID
    tech_card_code: str
    tech_card_version: int
    status: ProductionOrderStatus
    occurred_at: datetime
    batch_count: Decimal
    created_at: datetime
    lines: list[ProductionOrderLineItem]
    comment: str | None = None
    posted_at: datetime | None = None
    warehouse_name: str | None = None


@dataclass(frozen=True, slots=True)
class ProductionOrderPage:
    items: list[ProductionOrderListItem]
    total: int
