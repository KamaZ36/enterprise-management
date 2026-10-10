from collections.abc import Iterable, Sequence
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import RowMapping, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_balance import (
    StockBalance,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_balance.base import (
    BalanceKey,
    StockBalanceRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_BALANCES_TABLE,
)

AVERAGE_SCALE = Decimal("0.000001")


class SQLAlchemyStockBalanceRepository(StockBalanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_many(
        self, keys: Iterable[BalanceKey]
    ) -> dict[BalanceKey, StockBalance]:
        unique = sorted(set(keys))
        if not unique:
            return {}

        # Строки баланса может ещё не быть: создаём её, ничего не перезаписывая,
        # и только потом блокируем. Без этого параллельные приходы на новую
        # пару (склад, номенклатура) оба вставили бы строку.
        await self._session.execute(
            pg_insert(STOCK_BALANCES_TABLE)
            .values(
                [
                    {"warehouse_id": warehouse_id, "nomenclature_id": nomenclature_id}
                    for warehouse_id, nomenclature_id in unique
                ]
            )
            .on_conflict_do_nothing(index_elements=["warehouse_id", "nomenclature_id"])
        )

        stmt = (
            select(STOCK_BALANCES_TABLE)
            .where(
                tuple_(
                    STOCK_BALANCES_TABLE.c.warehouse_id,
                    STOCK_BALANCES_TABLE.c.nomenclature_id,
                ).in_(unique)
            )
            .order_by(
                STOCK_BALANCES_TABLE.c.warehouse_id,
                STOCK_BALANCES_TABLE.c.nomenclature_id,
            )
            .with_for_update()
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return {
            (row["warehouse_id"], row["nomenclature_id"]): self._to_entity(row)
            for row in rows
        }

    async def save_many(self, balances: Sequence[StockBalance]) -> None:
        if not balances:
            return

        values = [
            {
                "warehouse_id": balance.warehouse_id,
                "nomenclature_id": balance.nomenclature_id,
                "quantity": balance.quantity,
                "average_unit_cost": balance.average_unit_cost.quantize(
                    AVERAGE_SCALE, rounding=ROUND_HALF_UP
                ),
                "total_value": balance.total_value.kopecks,
                "updated_at": balance.updated_at,
            }
            for balance in balances
        ]

        stmt = pg_insert(STOCK_BALANCES_TABLE).values(values)
        await self._session.execute(
            stmt.on_conflict_do_update(
                index_elements=["warehouse_id", "nomenclature_id"],
                set_={
                    "quantity": stmt.excluded.quantity,
                    "average_unit_cost": stmt.excluded.average_unit_cost,
                    "total_value": stmt.excluded.total_value,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
        )

    async def get(
        self, warehouse_id: UUID, nomenclature_id: UUID
    ) -> StockBalance | None:
        stmt = select(STOCK_BALANCES_TABLE).where(
            STOCK_BALANCES_TABLE.c.warehouse_id == warehouse_id,
            STOCK_BALANCES_TABLE.c.nomenclature_id == nomenclature_id,
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def list_by_warehouse(self, warehouse_id: UUID) -> list[StockBalance]:
        stmt = (
            select(STOCK_BALANCES_TABLE)
            .where(STOCK_BALANCES_TABLE.c.warehouse_id == warehouse_id)
            .order_by(STOCK_BALANCES_TABLE.c.nomenclature_id.asc())
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_entity(row) for row in rows]

    def _to_entity(self, row: RowMapping) -> StockBalance:
        return StockBalance(
            warehouse_id=row["warehouse_id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            total_value=Money(kopecks=row["total_value"]),
            updated_at=row["updated_at"],
        )
