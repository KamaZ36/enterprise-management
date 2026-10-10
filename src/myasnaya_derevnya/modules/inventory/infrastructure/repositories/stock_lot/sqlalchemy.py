from uuid import UUID

from sqlalchemy import RowMapping, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_lot import StockLot
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_lot.base import (
    StockLotRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_LOTS_TABLE,
)


class SQLAlchemyStockLotRepository(StockLotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, lot: StockLot) -> None:
        await self._session.execute(
            insert(STOCK_LOTS_TABLE).values(
                id=lot.id,
                nomenclature_id=lot.nomenclature_id,
                lot_code=lot.lot_code,
                produced_at=lot.produced_at,
                expires_at=lot.expires_at,
                supplier_name=lot.supplier_name,
                created_at=lot.created_at,
            )
        )

    async def get_by_id(self, lot_id: UUID) -> StockLot | None:
        stmt = select(STOCK_LOTS_TABLE).where(STOCK_LOTS_TABLE.c.id == lot_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_by_code(
        self, nomenclature_id: UUID, lot_code: str
    ) -> StockLot | None:
        stmt = select(STOCK_LOTS_TABLE).where(
            STOCK_LOTS_TABLE.c.nomenclature_id == nomenclature_id,
            STOCK_LOTS_TABLE.c.lot_code == lot_code,
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    def _to_entity(self, row: RowMapping) -> StockLot:
        return StockLot(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            lot_code=row["lot_code"],
            produced_at=row["produced_at"],
            expires_at=row["expires_at"],
            supplier_name=row["supplier_name"],
            created_at=row["created_at"],
        )
