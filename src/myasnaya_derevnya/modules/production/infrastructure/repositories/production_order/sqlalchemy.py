from uuid import UUID

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.production.domain.entities.production_order import (
    ProductionOrder,
    ProductionOrderLine,
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
from myasnaya_derevnya.modules.production.infrastructure.repositories.production_order.base import (
    ProductionOrderRepository,
)
from myasnaya_derevnya.modules.production.infrastructure.tables import (
    PRODUCTION_ORDER_LINES_TABLE,
    PRODUCTION_ORDERS_TABLE,
)


class SQLAlchemyProductionOrderRepository(ProductionOrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: ProductionOrder) -> None:
        await self._session.execute(
            insert(PRODUCTION_ORDERS_TABLE).values(**self._order_values(order))
        )

        if order.lines:
            await self._session.execute(
                insert(PRODUCTION_ORDER_LINES_TABLE).values(
                    [self._line_values(order.id, line) for line in order.lines]
                )
            )

    async def save(self, order: ProductionOrder) -> None:
        values = self._order_values(order)
        values.pop("id", None)
        values.pop("created_at", None)

        await self._session.execute(
            update(PRODUCTION_ORDERS_TABLE)
            .where(PRODUCTION_ORDERS_TABLE.c.id == order.id)
            .values(**values)
        )


        await self._session.execute(
            delete(PRODUCTION_ORDER_LINES_TABLE).where(
                PRODUCTION_ORDER_LINES_TABLE.c.order_id == order.id
            )
        )

        if order.lines:
            await self._session.execute(
                insert(PRODUCTION_ORDER_LINES_TABLE).values(
                    [self._line_values(order.id, line) for line in order.lines]
                )
            )

    async def get_by_id(self, order_id: UUID) -> ProductionOrder | None:
        row = (
            (
                await self._session.execute(
                    select(PRODUCTION_ORDERS_TABLE).where(
                        PRODUCTION_ORDERS_TABLE.c.id == order_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        lines = (
            (
                await self._session.execute(
                    select(PRODUCTION_ORDER_LINES_TABLE)
                    .where(PRODUCTION_ORDER_LINES_TABLE.c.order_id == order_id)
                    .order_by(PRODUCTION_ORDER_LINES_TABLE.c.id.asc())
                )
            )
            .mappings()
            .all()
        )

        return self._to_entity(row, lines)

    def _order_values(self, order: ProductionOrder) -> dict[str, object]:
        return {
            "id": order.id,
            "warehouse_id": order.warehouse_id,
            "tech_card_id": order.tech_card_id,
            "tech_card_code": order.tech_card_code,
            "tech_card_version": order.tech_card_version,
            "status": order.status.value,
            "occurred_at": order.occurred_at,
            "batch_count": order.batch_count,
            "comment": order.comment,
            "created_by": order.created_by,
            "created_at": order.created_at,
            "posted_at": order.posted_at,
        }

    def _line_values(
        self, order_id: UUID, line: ProductionOrderLine
    ) -> dict[str, object]:
        return {
            "id": line.id,
            "order_id": order_id,
            "role": line.role.value,
            "nomenclature_id": line.nomenclature_id,
            "loss_kind": line.loss_kind.value if line.loss_kind else None,
            "output_kind": line.output_kind.value if line.output_kind else None,
            "cost_coefficient": line.cost_coefficient,
            "planned_quantity": line.planned_quantity,
            "actual_quantity": line.actual_quantity,
            "cost": line.cost_kopecks,
        }

    def _to_entity(self, row, lines) -> ProductionOrder:
        return ProductionOrder(
            id=row["id"],
            warehouse_id=row["warehouse_id"],
            tech_card_id=row["tech_card_id"],
            tech_card_code=row["tech_card_code"],
            tech_card_version=row["tech_card_version"],
            status=ProductionOrderStatus(row["status"]),
            occurred_at=row["occurred_at"],
            batch_count=row["batch_count"],
            created_at=row["created_at"],
            lines=[
                ProductionOrderLine(
                    id=line["id"],
                    role=SpecLineRole(line["role"]),
                    planned_quantity=line["planned_quantity"],
                    actual_quantity=line["actual_quantity"],
                    nomenclature_id=line["nomenclature_id"],
                    loss_kind=LossKind(line["loss_kind"])
                    if line["loss_kind"]
                    else None,
                    output_kind=OutputKind(line["output_kind"])
                    if line["output_kind"]
                    else None,
                    cost_coefficient=line["cost_coefficient"],
                    cost_kopecks=line["cost"],
                )
                for line in lines
            ],
            created_by=row["created_by"],
            comment=row["comment"],
            posted_at=row["posted_at"],
        )
