from uuid import UUID

from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem
from myasnaya_derevnya.modules.inventory.infrastructure.readers.balance.base import (
    BalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_BALANCES_TABLE,
)

BASE_COLUMNS = (
    STOCK_BALANCES_TABLE.c.warehouse_id,
    STOCK_BALANCES_TABLE.c.nomenclature_id,
    STOCK_BALANCES_TABLE.c.quantity,
)

COST_COLUMNS = (
    STOCK_BALANCES_TABLE.c.average_unit_cost,
    STOCK_BALANCES_TABLE.c.total_value,
)


class SQLAlchemyBalanceReader(BalanceReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_warehouse(
        self, warehouse_id: UUID, *, with_cost: bool
    ) -> list[BalanceListItem]:
        stmt = (
            select(*self._columns(with_cost))
            .where(STOCK_BALANCES_TABLE.c.warehouse_id == warehouse_id)
            .order_by(STOCK_BALANCES_TABLE.c.nomenclature_id.asc())
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_dto(row, with_cost=with_cost) for row in rows]

    async def get(
        self, warehouse_id: UUID, nomenclature_id: UUID, *, with_cost: bool
    ) -> BalanceListItem | None:
        stmt = select(*self._columns(with_cost)).where(
            STOCK_BALANCES_TABLE.c.warehouse_id == warehouse_id,
            STOCK_BALANCES_TABLE.c.nomenclature_id == nomenclature_id,
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        return self._to_dto(row, with_cost=with_cost) if row is not None else None

    @staticmethod
    def _columns(with_cost: bool) -> tuple:
        return BASE_COLUMNS + COST_COLUMNS if with_cost else BASE_COLUMNS

    @staticmethod
    def _to_dto(row: RowMapping, *, with_cost: bool) -> BalanceListItem:
        return BalanceListItem(
            warehouse_id=row["warehouse_id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            average_unit_cost=row["average_unit_cost"] if with_cost else None,
            total_value_kopecks=row["total_value"] if with_cost else None,
        )
