from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid7

from myasnaya_derevnya.modules.production.domain.entities.tech_card import TechCard
from myasnaya_derevnya.modules.production.domain.errors import (
    EmptyBatchError,
    EmptyProductionInputError,
    EmptyProductionOutputError,
    OutputExceedsInputError,
    ProductionOrderLineNotFoundError,
    ProductionOrderNotDraftError,
)
from myasnaya_derevnya.modules.production.domain.services.quantity_split import (
    split_quantity,
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
from myasnaya_derevnya.utils import get_datetime_utc

ONE = Decimal(1)


@dataclass(frozen=True, slots=True)
class ProductionOrderLine:
    id: UUID
    role: SpecLineRole
    planned_quantity: Decimal
    actual_quantity: Decimal
    nomenclature_id: UUID | None = None
    loss_kind: LossKind | None = None
    output_kind: OutputKind | None = None
    cost_coefficient: Decimal | None = None
    cost_kopecks: int | None = None

    def with_actual(self, quantity: Decimal) -> ProductionOrderLine:
        return replace(self, actual_quantity=quantity)

    def with_cost(self, kopecks: int) -> ProductionOrderLine:
        return replace(self, cost_kopecks=kopecks)

    @property
    def cost_weight(self) -> Decimal:
        coefficient = (
            self.cost_coefficient if self.cost_coefficient is not None else ONE
        )

        return self.actual_quantity * coefficient


class ProductionOrder:
    def __init__(
        self,
        id: UUID,
        warehouse_id: UUID,
        tech_card_id: UUID,
        tech_card_code: str,
        tech_card_version: int,
        status: ProductionOrderStatus,
        occurred_at: datetime,
        batch_count: Decimal,
        created_at: datetime,
        lines: list[ProductionOrderLine],
        created_by: UUID | None = None,
        comment: str | None = None,
        posted_at: datetime | None = None,
    ) -> None:
        self._id = id
        self._warehouse_id = warehouse_id
        self._tech_card_id = tech_card_id
        self._tech_card_code = tech_card_code
        self._tech_card_version = tech_card_version
        self._status = status
        self._occurred_at = occurred_at
        self._batch_count = batch_count
        self._created_at = created_at
        self._lines = lines
        self._created_by = created_by
        self._comment = comment
        self._posted_at = posted_at

    @classmethod
    def create(
        cls,
        *,
        warehouse_id: UUID,
        tech_card: TechCard,
        batch_count: Decimal,
        occurred_at: datetime,
        created_by: UUID | None = None,
        comment: str | None = None,
    ) -> ProductionOrder:
        if batch_count <= 0:
            raise EmptyBatchError()

        lines = [
            ProductionOrderLine(
                id=uuid7(),
                role=line.role,
                planned_quantity=line.quantity * batch_count,
                actual_quantity=line.quantity * batch_count,
                nomenclature_id=line.nomenclature_id,
                loss_kind=line.loss_kind,
                output_kind=line.output_kind,
                cost_coefficient=line.cost_coefficient,
            )
            for line in tech_card.lines
        ]

        return cls(
            id=uuid7(),
            warehouse_id=warehouse_id,
            tech_card_id=tech_card.id,
            tech_card_code=tech_card.code,
            tech_card_version=tech_card.version,
            status=ProductionOrderStatus.DRAFT,
            occurred_at=occurred_at,
            batch_count=batch_count,
            created_at=get_datetime_utc(),
            lines=lines,
            created_by=created_by,
            comment=comment,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def warehouse_id(self) -> UUID:
        return self._warehouse_id

    @property
    def tech_card_id(self) -> UUID:
        return self._tech_card_id

    @property
    def tech_card_code(self) -> str:
        return self._tech_card_code

    @property
    def tech_card_version(self) -> int:
        return self._tech_card_version

    @property
    def status(self) -> ProductionOrderStatus:
        return self._status

    @property
    def occurred_at(self) -> datetime:
        return self._occurred_at

    @property
    def batch_count(self) -> Decimal:
        return self._batch_count

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def created_by(self) -> UUID | None:
        return self._created_by

    @property
    def comment(self) -> str | None:
        return self._comment

    @property
    def posted_at(self) -> datetime | None:
        return self._posted_at

    @property
    def is_draft(self) -> bool:
        return self._status is ProductionOrderStatus.DRAFT

    @property
    def lines(self) -> list[ProductionOrderLine]:
        return list(self._lines)

    @property
    def components(self) -> list[ProductionOrderLine]:
        return [line for line in self._lines if line.role is SpecLineRole.COMPONENT]

    @property
    def outputs(self) -> list[ProductionOrderLine]:
        return [line for line in self._lines if line.role is SpecLineRole.OUTPUT]

    @property
    def losses(self) -> list[ProductionOrderLine]:
        return [line for line in self._lines if line.role is SpecLineRole.LOSS]

    def set_actual(self, line_id: UUID, quantity: Decimal) -> None:
        if not self.is_draft:
            raise ProductionOrderNotDraftError()
        if not any(line.id == line_id for line in self._lines):
            raise ProductionOrderLineNotFoundError(line_id)

        self._lines = [
            line.with_actual(quantity) if line.id == line_id else line
            for line in self._lines
        ]

    def post(self) -> None:
        if not self.is_draft:
            raise ProductionOrderNotDraftError()

        inputs = sum(
            (line.actual_quantity for line in self.components), start=Decimal(0)
        )
        outputs = sum(
            (line.actual_quantity for line in self.outputs), start=Decimal(0)
        )

        if not self.outputs or outputs <= 0:
            raise EmptyProductionOutputError()
        if not self.components or inputs <= 0:
            raise EmptyProductionInputError()

        residual = inputs - outputs
        if residual < 0:
            raise OutputExceedsInputError()

        self._lines = [
            *self.components,
            *self.outputs,
            *self._loss_lines(residual),
        ]
        self._status = ProductionOrderStatus.POSTED
        self._posted_at = get_datetime_utc()

    def apply_costs(self, costs: Mapping[UUID, int]) -> None:
        self._lines = [
            line.with_cost(costs[line.id]) if line.id in costs else line
            for line in self._lines
        ]

    def cancel(self) -> None:
        if not self.is_draft:
            raise ProductionOrderNotDraftError()

        self._status = ProductionOrderStatus.CANCELLED

    def _loss_lines(self, residual: Decimal) -> list[ProductionOrderLine]:
        planned = self.losses

        if residual == 0:
            return [line.with_actual(Decimal(0)) for line in planned]
        if not planned:
            return [
                ProductionOrderLine(
                    id=uuid7(),
                    role=SpecLineRole.LOSS,
                    planned_quantity=residual,
                    actual_quantity=residual,
                )
            ]

        parts = split_quantity(residual, [line.planned_quantity for line in planned])

        return [
            line.with_actual(part)
            for line, part in zip(planned, parts, strict=True)
        ]
