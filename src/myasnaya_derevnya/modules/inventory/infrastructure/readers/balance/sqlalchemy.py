from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.application.dto import BalanceListItem
from myasnaya_derevnya.modules.inventory.infrastructure.readers.balance.base import (
    BalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_BALANCES_TABLE,
)

BASE_COLUMNS = (
    STOCK_BALANCES_TABLE.c.org_unit_id,
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

    async def list_by_org_unit(
        self,
        org_unit_id: UUID,
        *,
        with_cost: bool,
        nomenclature_ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[BalanceListItem], int]:
        conditions = [STOCK_BALANCES_TABLE.c.org_unit_id == org_unit_id]

        if nomenclature_ids is not None:
            conditions.append(
                STOCK_BALANCES_TABLE.c.nomenclature_id.in_(nomenclature_ids)
            )

        total = await self._session.scalar(
            select(func.count()).select_from(STOCK_BALANCES_TABLE).where(*conditions)
        )

        stmt = (
            select(*self._columns(with_cost))
            .where(*conditions)
            .order_by(STOCK_BALANCES_TABLE.c.nomenclature_id.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return (
            [self._to_dto(row, with_cost=with_cost) for row in rows],
            int(total or 0),
        )

    async def get(
        self, org_unit_id: UUID, nomenclature_id: UUID, *, with_cost: bool
    ) -> BalanceListItem | None:
        stmt = select(*self._columns(with_cost)).where(
            STOCK_BALANCES_TABLE.c.org_unit_id == org_unit_id,
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
            org_unit_id=row["org_unit_id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            average_unit_cost=row["average_unit_cost"] if with_cost else None,
            total_value_kopecks=row["total_value"] if with_cost else None,
        )
