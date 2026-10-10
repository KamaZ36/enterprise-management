from collections.abc import Iterable, Sequence

from sqlalchemy import RowMapping, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot_balance import (
    StockLotBalance,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot_balance.base import (
    LotBalanceKey,
    StockLotBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_LOT_BALANCES_TABLE,
)


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
                        "warehouse_id": warehouse_id,
                        "nomenclature_id": nomenclature_id,
                        "lot_id": lot_id,
                    }
                    for warehouse_id, nomenclature_id, lot_id in unique
                ]
            )
            .on_conflict_do_nothing(
                index_elements=["warehouse_id", "nomenclature_id", "lot_id"]
            )
        )

        stmt = (
            select(STOCK_LOT_BALANCES_TABLE)
            .where(
                tuple_(
                    STOCK_LOT_BALANCES_TABLE.c.warehouse_id,
                    STOCK_LOT_BALANCES_TABLE.c.nomenclature_id,
                    STOCK_LOT_BALANCES_TABLE.c.lot_id,
                ).in_(unique)
            )
            .order_by(
                STOCK_LOT_BALANCES_TABLE.c.warehouse_id,
                STOCK_LOT_BALANCES_TABLE.c.nomenclature_id,
                STOCK_LOT_BALANCES_TABLE.c.lot_id,
            )
            .with_for_update()
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return {
            (row["warehouse_id"], row["nomenclature_id"], row["lot_id"]): (
                self._to_entity(row)
            )
            for row in rows
        }

    async def save_many(self, balances: Sequence[StockLotBalance]) -> None:
        if not balances:
            return

        values = [
            {
                "warehouse_id": balance.warehouse_id,
                "nomenclature_id": balance.nomenclature_id,
                "lot_id": balance.lot_id,
                "quantity": balance.quantity,
            }
            for balance in balances
        ]

        stmt = pg_insert(STOCK_LOT_BALANCES_TABLE).values(values)
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["warehouse_id", "nomenclature_id", "lot_id"],
                set_={"quantity": stmt.excluded.quantity},
            )
        )

    def _to_entity(self, row: RowMapping) -> StockLotBalance:
        return StockLotBalance(
            warehouse_id=row["warehouse_id"],
            nomenclature_id=row["nomenclature_id"],
            lot_id=row["lot_id"],
            quantity=row["quantity"],
        )
