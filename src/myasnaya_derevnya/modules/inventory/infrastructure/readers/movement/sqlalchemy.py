from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import RowMapping, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.dto import MovementListItem
from myasnaya_derevnya.modules.inventory.infrastructure.readers.movement.base import (
    MovementReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_LOTS_TABLE,
    STOCK_MOVEMENTS_TABLE,
)


class SQLAlchemyMovementReader(MovementReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        nomenclature_id: UUID | None = None,
        movement_types: Sequence[str] = (),
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MovementListItem], int]:
        conditions = []
        if org_unit_ids is not None:
            conditions.append(STOCK_MOVEMENTS_TABLE.c.org_unit_id.in_(org_unit_ids))

        if nomenclature_id is not None:
            conditions.append(
                STOCK_MOVEMENTS_TABLE.c.nomenclature_id == nomenclature_id
            )

        if movement_types:
            conditions.append(
                STOCK_MOVEMENTS_TABLE.c.movement_type.in_(movement_types)
            )

        if occurred_from is not None:
            conditions.append(STOCK_MOVEMENTS_TABLE.c.occurred_at >= occurred_from)

        if occurred_to is not None:
            conditions.append(STOCK_MOVEMENTS_TABLE.c.occurred_at <= occurred_to)

        total = await self._session.scalar(
            select(func.count()).select_from(STOCK_MOVEMENTS_TABLE).where(*conditions)
        )

        stmt = (
            select(
                STOCK_MOVEMENTS_TABLE.c.id,
                STOCK_MOVEMENTS_TABLE.c.occurred_at,
                STOCK_MOVEMENTS_TABLE.c.org_unit_id,
                STOCK_MOVEMENTS_TABLE.c.nomenclature_id,
                STOCK_MOVEMENTS_TABLE.c.lot_id,
                STOCK_MOVEMENTS_TABLE.c.movement_type,
                STOCK_MOVEMENTS_TABLE.c.quantity,
                STOCK_MOVEMENTS_TABLE.c.total_cost,
                STOCK_LOTS_TABLE.c.lot_code,
            )
            .select_from(
                STOCK_MOVEMENTS_TABLE.outerjoin(
                    STOCK_LOTS_TABLE,
                    STOCK_MOVEMENTS_TABLE.c.lot_id == STOCK_LOTS_TABLE.c.id,
                )
            )
            .where(*conditions)
            .order_by(
                STOCK_MOVEMENTS_TABLE.c.occurred_at.desc(),
                STOCK_MOVEMENTS_TABLE.c.recorded_at.desc(),
                STOCK_MOVEMENTS_TABLE.c.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row) for row in rows], total or 0

    @staticmethod
    def _to_dto(row: RowMapping) -> MovementListItem:
        return MovementListItem(
            id=row["id"],
            occurred_at=row["occurred_at"],
            org_unit_id=row["org_unit_id"],
            nomenclature_id=row["nomenclature_id"],
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
            movement_type=row["movement_type"],
            quantity=row["quantity"],
            total_cost_kopecks=row["total_cost"],
        )
