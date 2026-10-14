from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.production.application.dto import (
    ProductionOrderListItem,
)
from myasnaya_derevnya.modules.production.domain.value_objects.order_status import (
    ProductionOrderStatus,
)
from myasnaya_derevnya.modules.production.infrastructure.readers.production_order.base import (
    ProductionOrderReader,
)
from myasnaya_derevnya.modules.production.infrastructure.tables import (
    PRODUCTION_ORDERS_TABLE,
)


class SQLAlchemyProductionOrderReader(ProductionOrderReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        warehouse_ids: Sequence[UUID] | None,
        statuses: Sequence[str] | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ProductionOrderListItem], int]:
        conditions = []

        if warehouse_ids is not None:
            conditions.append(
                PRODUCTION_ORDERS_TABLE.c.warehouse_id.in_(list(warehouse_ids))
            )
        if statuses:
            conditions.append(PRODUCTION_ORDERS_TABLE.c.status.in_(list(statuses)))
        if occurred_from is not None:
            conditions.append(
                PRODUCTION_ORDERS_TABLE.c.occurred_at >= occurred_from
            )
        if occurred_to is not None:
            conditions.append(PRODUCTION_ORDERS_TABLE.c.occurred_at < occurred_to)

        total = await self._session.scalar(
            select(func.count())
            .select_from(PRODUCTION_ORDERS_TABLE)
            .where(*conditions)
        )

        rows = (
            (
                await self._session.execute(
                    select(PRODUCTION_ORDERS_TABLE)
                    .where(*conditions)
                    .order_by(
                        PRODUCTION_ORDERS_TABLE.c.occurred_at.desc(),
                        PRODUCTION_ORDERS_TABLE.c.created_at.desc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .mappings()
            .all()
        )

        return (
            [
                ProductionOrderListItem(
                    id=row["id"],
                    warehouse_id=row["warehouse_id"],
                    tech_card_id=row["tech_card_id"],
                    tech_card_code=row["tech_card_code"],
                    tech_card_version=row["tech_card_version"],
                    status=ProductionOrderStatus(row["status"]),
                    occurred_at=row["occurred_at"],
                    batch_count=row["batch_count"],
                    created_at=row["created_at"],
                    posted_at=row["posted_at"],
                )
                for row in rows
            ],
            int(total or 0),
        )
