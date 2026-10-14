from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.sales.application.dto import (
    OrderDetail,
    OrderLineItem,
    OrderListItem,
)
from myasnaya_derevnya.modules.sales.infrastructure.readers.order.base import (
    OrderReader,
)
from myasnaya_derevnya.modules.sales.infrastructure.tables import (
    ORDER_LINES_TABLE,
    ORDERS_TABLE,
)


class SQLAlchemyOrderReader(OrderReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_ids: list[UUID] | None = None,
        statuses: list[str] | None = None,
        day: date | None = None,
        customer_id: UUID | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OrderListItem], int]:
        conditions = self._conditions(
            org_unit_ids=org_unit_ids,
            statuses=statuses,
            day=day,
            customer_id=customer_id,
            search=search,
        )

        total = await self._session.scalar(
            select(func.count()).select_from(ORDERS_TABLE).where(*conditions)
        )

        rows = (
            (
                await self._session.execute(
                    select(ORDERS_TABLE)
                    .where(*conditions)
                    .order_by(
                        ORDERS_TABLE.c.created_at.desc(), ORDERS_TABLE.c.id.desc()
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        if not rows:
            return [], int(total or 0)

        order_ids = [row["id"] for row in rows]
        sums = {
            line["order_id"]: (line["total"] or 0, line["lines"] or 0)
            for line in (
                await self._session.execute(
                    select(
                        ORDER_LINES_TABLE.c.order_id,
                        func.sum(
                            ORDER_LINES_TABLE.c.quantity
                            * ORDER_LINES_TABLE.c.unit_price
                        ).label("total"),
                        func.count().label("lines"),
                    )
                    .where(ORDER_LINES_TABLE.c.order_id.in_(order_ids))
                    .group_by(ORDER_LINES_TABLE.c.order_id)
                )
            )
            .mappings()
            .all()
        }

        items = [
            OrderListItem(
                id=row["id"],
                number=row["number"],
                status=row["status"],
                channel=row["channel"],
                org_unit_id=row["org_unit_id"],
                customer_id=row["customer_id"],
                created_at=row["created_at"],
                planned_at=row["planned_at"],
                total=int(sums.get(row["id"], (0, 0))[0]),
                line_count=int(sums.get(row["id"], (0, 0))[1]),
            )
            for row in rows
        ]

        return items, int(total or 0)

    async def get(self, order_id: UUID) -> OrderDetail | None:
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

        items = [
            OrderLineItem(
                nomenclature_id=line["nomenclature_id"],
                nomenclature_name=None,
                quantity=line["quantity"],
                unit_price=line["unit_price"],
                total=int(Decimal(line["quantity"]) * line["unit_price"]),
            )
            for line in lines
        ]

        return OrderDetail(
            id=row["id"],
            number=row["number"],
            status=row["status"],
            channel=row["channel"],
            org_unit_id=row["org_unit_id"],
            customer_id=row["customer_id"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            planned_at=row["planned_at"],
            comment=row["comment"],
            contact_phone=row["contact_phone"],
            completed_at=row["completed_at"],
            cancelled_at=row["cancelled_at"],
            total=sum(item.total for item in items),
            lines=items,
        )

    def _conditions(
        self,
        *,
        org_unit_ids: list[UUID] | None,
        statuses: list[str] | None,
        day: date | None,
        customer_id: UUID | None,
        search: str | None,
    ) -> list[object]:
        conditions: list[object] = []

        if org_unit_ids is not None:
            conditions.append(ORDERS_TABLE.c.org_unit_id.in_(org_unit_ids))

        if statuses:
            conditions.append(ORDERS_TABLE.c.status.in_(statuses))

        if day is not None:
            conditions.append(ORDERS_TABLE.c.day == day)

        if customer_id is not None:
            conditions.append(ORDERS_TABLE.c.customer_id == customer_id)

        if search:
            tokens = [
                or_(
                    ORDERS_TABLE.c.comment.ilike(like_pattern(token), escape="\\"),
                    func.cast(
                        ORDERS_TABLE.c.number, __import__("sqlalchemy").String
                    ).ilike(like_pattern(token), escape="\\"),
                )
                for token in search.split()
            ]
            conditions.extend(tokens)

        return conditions
