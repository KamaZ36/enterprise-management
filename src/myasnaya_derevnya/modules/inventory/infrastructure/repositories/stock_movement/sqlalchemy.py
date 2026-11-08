from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, exists, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
    StockMovement,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
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

    async def list_by_posting(self, posting_id: UUID) -> list[StockMovement]:
        stmt = select(STOCK_MOVEMENTS_TABLE).where(
            STOCK_MOVEMENTS_TABLE.c.posting_id == posting_id
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_entity(row) for row in rows]

    async def delete_by_posting(self, posting_id: UUID) -> None:
        await self._session.execute(
            delete(STOCK_MOVEMENTS_TABLE).where(
                STOCK_MOVEMENTS_TABLE.c.posting_id == posting_id
            )
        )

    async def has_later_movements(
        self,
        *,
        posting_id: UUID,
        since: datetime,
        org_unit_id: UUID,
        nomenclature_id: UUID,
    ) -> bool:
        stmt = select(
            exists().where(
                STOCK_MOVEMENTS_TABLE.c.org_unit_id == org_unit_id,
                STOCK_MOVEMENTS_TABLE.c.nomenclature_id == nomenclature_id,
                STOCK_MOVEMENTS_TABLE.c.posting_id != posting_id,
                STOCK_MOVEMENTS_TABLE.c.recorded_at > since,
            )
        )

        return bool(await self._session.scalar(stmt))

    def _to_entity(self, row) -> StockMovement:
        return StockMovement(
            id=row["id"],
            occurred_at=row["occurred_at"],
            recorded_at=row["recorded_at"],
            org_unit_id=row["org_unit_id"],
            nomenclature_id=row["nomenclature_id"],
            lot_id=row["lot_id"],
            movement_type=MovementType(row["movement_type"]),
            quantity=row["quantity"],
            total_cost=Money(kopecks=row["total_cost"]),
            posting_id=row["posting_id"],
            created_by=row["created_by"],
        )
