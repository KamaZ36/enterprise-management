from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import RowMapping, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot_balance import (
    StockLotBalance,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.base import (
    LotBalanceKey,
    StockLotBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_LOT_BALANCES_TABLE,
    STOCK_LOTS_TABLE,
)

AVERAGE_SCALE = Decimal("0.000001")


class SQLAlchemyStockLotBalanceRepository(StockLotBalanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_many(
        self, keys: Iterable[LotBalanceKey]
    ) -> dict[LotBalanceKey, StockLotBalance]:
        unique = sorted(set(keys))
        if not unique:
            return {}

        await self._session.execute(
            pg_insert(STOCK_LOT_BALANCES_TABLE)
            .values(
                [
                    {
                        "org_unit_id": org_unit_id,
                        "nomenclature_id": nomenclature_id,
                        "lot_id": lot_id,
                    }
                    for org_unit_id, nomenclature_id, lot_id in unique
                ]
            )
            .on_conflict_do_nothing(
                index_elements=["org_unit_id", "nomenclature_id", "lot_id"]
            )
        )

        stmt = (
            select(STOCK_LOT_BALANCES_TABLE)
            .where(
                tuple_(
                    STOCK_LOT_BALANCES_TABLE.c.org_unit_id,
                    STOCK_LOT_BALANCES_TABLE.c.nomenclature_id,
                    STOCK_LOT_BALANCES_TABLE.c.lot_id,
                ).in_(unique)
            )
            .order_by(
                STOCK_LOT_BALANCES_TABLE.c.org_unit_id,
                STOCK_LOT_BALANCES_TABLE.c.nomenclature_id,
                STOCK_LOT_BALANCES_TABLE.c.lot_id,
            )
            .with_for_update()
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return {
            (row["org_unit_id"], row["nomenclature_id"], row["lot_id"]): (
                self._to_entity(row)
            )
            for row in rows
        }

    async def list_available(
        self, org_unit_id: UUID, nomenclature_id: UUID
    ) -> list[StockLotBalance]:
        stmt = (
            select(STOCK_LOT_BALANCES_TABLE)
            .select_from(
                STOCK_LOT_BALANCES_TABLE.outerjoin(
                    STOCK_LOTS_TABLE,
                    STOCK_LOT_BALANCES_TABLE.c.lot_id == STOCK_LOTS_TABLE.c.id,
                )
            )
            .where(
                STOCK_LOT_BALANCES_TABLE.c.org_unit_id == org_unit_id,
                STOCK_LOT_BALANCES_TABLE.c.nomenclature_id == nomenclature_id,
                STOCK_LOT_BALANCES_TABLE.c.quantity > 0,
            )
            .order_by(
                STOCK_LOTS_TABLE.c.expires_at.asc().nulls_last(),
                STOCK_LOTS_TABLE.c.created_at.asc(),
                STOCK_LOT_BALANCES_TABLE.c.lot_id.asc(),
            )
            .with_for_update(of=STOCK_LOT_BALANCES_TABLE)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_entity(row) for row in rows]

    async def save_many(self, balances: Sequence[StockLotBalance]) -> None:
        if not balances:
            return

        values = [
            {
                "org_unit_id": balance.org_unit_id,
                "nomenclature_id": balance.nomenclature_id,
                "lot_id": balance.lot_id,
                "quantity": balance.quantity,
                "total_value": balance.total_value.kopecks,
                "average_unit_cost": balance.average_unit_cost.quantize(
                    AVERAGE_SCALE, rounding=ROUND_HALF_UP
                ),
            }
            for balance in balances
        ]

        stmt = pg_insert(STOCK_LOT_BALANCES_TABLE).values(values)
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["org_unit_id", "nomenclature_id", "lot_id"],
                set_={
                    "quantity": stmt.excluded.quantity,
                    "total_value": stmt.excluded.total_value,
                    "average_unit_cost": stmt.excluded.average_unit_cost,
                },
            )
        )

    def _to_entity(self, row: RowMapping) -> StockLotBalance:
        return StockLotBalance(
            org_unit_id=row["org_unit_id"],
            nomenclature_id=row["nomenclature_id"],
            lot_id=row["lot_id"],
            quantity=row["quantity"],
            total_value=Money(kopecks=row["total_value"]),
        )
