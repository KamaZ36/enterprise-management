from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import LotBalanceListItem
from myasnaya_derevnya.modules.inventory.infrastructure.readers.lot_balance.base import (
    LotBalanceReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_LOT_BALANCES_TABLE,
    STOCK_LOTS_TABLE,
)


class SQLAlchemyLotBalanceReader(LotBalanceReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_org_unit(
        self,
        org_unit_id: UUID,
        *,
        with_cost: bool,
        include_empty: bool = False,
        expiring_before: date | None = None,
        search: str | None = None,
        nomenclature_ids: Sequence[UUID] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LotBalanceListItem], int]:
        source = STOCK_LOT_BALANCES_TABLE.join(
            STOCK_LOTS_TABLE,
            STOCK_LOT_BALANCES_TABLE.c.lot_id == STOCK_LOTS_TABLE.c.id,
        )
        conditions = [STOCK_LOT_BALANCES_TABLE.c.org_unit_id == org_unit_id]

        if not include_empty:
            conditions.append(STOCK_LOT_BALANCES_TABLE.c.quantity > 0)

        if expiring_before is not None:
            conditions.extend(
                [
                    STOCK_LOTS_TABLE.c.expires_at.is_not(None),
                    STOCK_LOTS_TABLE.c.expires_at <= expiring_before,
                ]
            )

        if search:
            conditions.append(
                or_(
                    STOCK_LOTS_TABLE.c.lot_code.ilike(
                        like_pattern(search), escape="\\"
                    ),
                    STOCK_LOT_BALANCES_TABLE.c.nomenclature_id.in_(
                        list(nomenclature_ids or [])
                    ),
                )
            )
        elif nomenclature_ids is not None:
            conditions.append(
                STOCK_LOT_BALANCES_TABLE.c.nomenclature_id.in_(nomenclature_ids)
            )

        total = await self._session.scalar(
            select(func.count()).select_from(source).where(*conditions)
        )

        stmt = (
            select(
                STOCK_LOT_BALANCES_TABLE.c.org_unit_id,
                STOCK_LOT_BALANCES_TABLE.c.nomenclature_id,
                STOCK_LOT_BALANCES_TABLE.c.lot_id,
                STOCK_LOT_BALANCES_TABLE.c.quantity,
                STOCK_LOT_BALANCES_TABLE.c.average_unit_cost,
                STOCK_LOT_BALANCES_TABLE.c.total_value,
                STOCK_LOTS_TABLE.c.lot_code,
                STOCK_LOTS_TABLE.c.expires_at,
                STOCK_LOTS_TABLE.c.produced_at,
                STOCK_LOTS_TABLE.c.supplier_name,
            )
            .select_from(source)
            .where(*conditions)
            .order_by(
                STOCK_LOTS_TABLE.c.expires_at.asc().nulls_last(),
                STOCK_LOT_BALANCES_TABLE.c.nomenclature_id.asc(),
                STOCK_LOTS_TABLE.c.lot_code.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return (
            [self._to_dto(row, with_cost=with_cost) for row in rows],
            int(total or 0),
        )

    @staticmethod
    def _to_dto(row: RowMapping, *, with_cost: bool) -> LotBalanceListItem:
        return LotBalanceListItem(
            org_unit_id=row["org_unit_id"],
            nomenclature_id=row["nomenclature_id"],
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
            quantity=row["quantity"],
            expires_at=row["expires_at"],
            produced_at=row["produced_at"],
            supplier_name=row["supplier_name"],
            unit_cost=row["average_unit_cost"] if with_cost else None,
            total_value_kopecks=row["total_value"] if with_cost else None,
        )
