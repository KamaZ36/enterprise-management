from datetime import date
from uuid import UUID

from sqlalchemy import RowMapping, delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.sales.domain.entities.order import (
    Order,
    OrderChannel,
    OrderLine,
    OrderStatus,
)
from myasnaya_derevnya.modules.sales.infrastructure.repositories.order.base import (
    OrderRepository,
)
from myasnaya_derevnya.modules.sales.infrastructure.tables import (
    ORDER_LINES_TABLE,
    ORDER_NUMBER_COUNTERS_TABLE,
    ORDERS_TABLE,
)


class SQLAlchemyOrderRepository(OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, order: Order) -> None:
        await self._session.execute(
            insert(ORDERS_TABLE).values(**self._order_values(order))
        )

        if order.lines:
            await self._session.execute(
                insert(ORDER_LINES_TABLE).values(
                    [self._line_values(order.id, line) for line in order.lines]
                )
            )

    async def save(self, order: Order) -> None:
        values = self._order_values(order)
        values.pop("id", None)
        values.pop("created_at", None)

        await self._session.execute(
            update(ORDERS_TABLE).where(ORDERS_TABLE.c.id == order.id).values(**values)
        )


        await self._session.execute(
            delete(ORDER_LINES_TABLE).where(ORDER_LINES_TABLE.c.order_id == order.id)
        )

        if order.lines:
            await self._session.execute(
                insert(ORDER_LINES_TABLE).values(
                    [self._line_values(order.id, line) for line in order.lines]
                )
            )

    async def get_by_id(self, order_id: UUID) -> Order | None:
        row = (
            (
                await self._session.execute(
                    select(ORDERS_TABLE).where(ORDERS_TABLE.c.id == order_id)
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
                    select(ORDER_LINES_TABLE)
                    .where(ORDER_LINES_TABLE.c.order_id == order_id)
                    .order_by(ORDER_LINES_TABLE.c.id.asc())
                )
            )
            .mappings()
            .all()
        )

        return self._to_entity(row, lines)

    async def next_number(self, org_unit_id: UUID, day: date) -> int:
        stmt = (
            pg_insert(ORDER_NUMBER_COUNTERS_TABLE)
            .values(org_unit_id=org_unit_id, day=day, last_number=1)
            .on_conflict_do_update(
                index_elements=[
                    ORDER_NUMBER_COUNTERS_TABLE.c.org_unit_id,
                    ORDER_NUMBER_COUNTERS_TABLE.c.day,
                ],
                set_={
                    "last_number": ORDER_NUMBER_COUNTERS_TABLE.c.last_number + 1,
                },
            )
            .returning(ORDER_NUMBER_COUNTERS_TABLE.c.last_number)
        )

        return int(await self._session.scalar(stmt))

    def _order_values(self, order: Order) -> dict[str, object]:
        return {
            "id": order.id,
            "org_unit_id": order.org_unit_id,
            "warehouse_id": order.warehouse_id,
            "channel": order.channel.value,
            "created_by": order.created_by,
            "customer_id": order.customer_id,
            "status": order.status.value,
            "number": order.number,
            "day": order.created_at.date(),
            "planned_at": order.planned_at,
            "comment": order.comment,
            "contact_phone": order.contact_phone,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "completed_at": order.completed_at,
            "cancelled_at": order.cancelled_at,
        }

    def _line_values(self, order_id: UUID, line: OrderLine) -> dict[str, object]:
        return {
            "id": line.id,
            "order_id": order_id,
            "nomenclature_id": line.nomenclature_id,
            "quantity": line.quantity,
            "unit_price": line.unit_price,
            "cost_kopecks": line.cost_kopecks,
        }

    def _to_entity(self, row: RowMapping, lines: list[RowMapping] | object) -> Order:
        return Order(
            id_=row["id"],
            org_unit_id=row["org_unit_id"],
            warehouse_id=row["warehouse_id"],
            channel=OrderChannel(row["channel"]),
            created_by=row["created_by"],
            customer_id=row["customer_id"],
            status=OrderStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            number=row["number"],
            planned_at=row["planned_at"],
            comment=row["comment"],
            completed_at=row["completed_at"],
            cancelled_at=row["cancelled_at"],
            contact_phone=row["contact_phone"],
            lines=[
                OrderLine(
                    id_=line["id"],
                    nomenclature_id=line["nomenclature_id"],
                    quantity=line["quantity"],
                    unit_price=line["unit_price"],
                    cost_kopecks=line["cost_kopecks"],
                )
                for line in lines
            ],
        )
