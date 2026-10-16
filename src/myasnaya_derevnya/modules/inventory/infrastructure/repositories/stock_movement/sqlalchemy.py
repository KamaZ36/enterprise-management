from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    StockMovement,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_movement.base import (
    StockMovementRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_MOVEMENTS_TABLE,
)


class SQLAlchemyStockMovementRepository(StockMovementRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_for_nomenclature(self, nomenclature_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(STOCK_MOVEMENTS_TABLE)
            .where(STOCK_MOVEMENTS_TABLE.c.nomenclature_id == nomenclature_id)
        )

        return total or 0

    async def add_many(self, movements: Sequence[StockMovement]) -> None:
        if not movements:
            return

        await self._session.execute(
            insert(STOCK_MOVEMENTS_TABLE).values(
                [
                    {
                        "id": movement.id,
                        "occurred_at": movement.occurred_at,
                        "recorded_at": movement.recorded_at,
                        "org_unit_id": movement.org_unit_id,
                        "nomenclature_id": movement.nomenclature_id,
                        "lot_id": movement.lot_id,
                        "movement_type": movement.movement_type.value,
                        "quantity": movement.quantity,
                        "total_cost": movement.total_cost.kopecks,
                        "posting_id": movement.posting_id,
                        "created_by": movement.created_by,
                    }
                    for movement in movements
                ]
            )
        )
