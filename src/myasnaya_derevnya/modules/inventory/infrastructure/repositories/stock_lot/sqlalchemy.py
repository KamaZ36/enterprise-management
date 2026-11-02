from datetime import date
from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
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
                origin_org_unit_id=lot.origin_org_unit_id,
                vetis_vsd_number=lot.vetis_vsd_number,
                vetis_vsd_guid=lot.vetis_vsd_guid,
                vetis_batch_id=lot.vetis_batch_id,
                vetis_product_item_guid=lot.vetis_product_item_guid,
                vetis_entered_at=lot.vetis_entered_at,
                vetis_entered_by=lot.vetis_entered_by,
                veterinary_document_id=lot.veterinary_document_id,
                created_at=lot.created_at,
            )
        )

    async def save(self, lot: StockLot) -> None:
        await self._session.execute(
            update(STOCK_LOTS_TABLE)
            .where(STOCK_LOTS_TABLE.c.id == lot.id)
            .values(
                supplier_name=lot.supplier_name,
                vetis_vsd_number=lot.vetis_vsd_number,
                vetis_vsd_guid=lot.vetis_vsd_guid,
                vetis_batch_id=lot.vetis_batch_id,
                vetis_product_item_guid=lot.vetis_product_item_guid,
                vetis_entered_at=lot.vetis_entered_at,
                vetis_entered_by=lot.vetis_entered_by,
                veterinary_document_id=lot.veterinary_document_id,
            )
        )

    async def get_by_id(self, lot_id: UUID) -> StockLot | None:
        stmt = select(STOCK_LOTS_TABLE).where(STOCK_LOTS_TABLE.c.id == lot_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def get_by_identity(
        self,
        nomenclature_id: UUID,
        lot_code: str,
        produced_at: date | None,
        supplier_name: str | None,
    ) -> StockLot | None:
        stmt = select(STOCK_LOTS_TABLE).where(
            STOCK_LOTS_TABLE.c.nomenclature_id == nomenclature_id,
            STOCK_LOTS_TABLE.c.lot_code == lot_code,
            STOCK_LOTS_TABLE.c.produced_at.is_not_distinct_from(produced_at),
            STOCK_LOTS_TABLE.c.supplier_name.is_not_distinct_from(supplier_name),
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        return self._to_entity(row)

    async def list_by_code(
        self, nomenclature_id: UUID, lot_code: str
    ) -> list[StockLot]:
        stmt = (
            select(STOCK_LOTS_TABLE)
            .where(
                STOCK_LOTS_TABLE.c.nomenclature_id == nomenclature_id,
                STOCK_LOTS_TABLE.c.lot_code == lot_code,
            )
            .order_by(STOCK_LOTS_TABLE.c.created_at.asc())
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_entity(row) for row in rows]

    def _to_entity(self, row: RowMapping) -> StockLot:
        return StockLot(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            lot_code=row["lot_code"],
            produced_at=row["produced_at"],
            expires_at=row["expires_at"],
            supplier_name=row["supplier_name"],
            origin_org_unit_id=row["origin_org_unit_id"],
            vetis_vsd_number=row["vetis_vsd_number"],
            vetis_vsd_guid=row["vetis_vsd_guid"],
            vetis_batch_id=row["vetis_batch_id"],
            vetis_product_item_guid=row["vetis_product_item_guid"],
            vetis_entered_at=row["vetis_entered_at"],
            vetis_entered_by=row["vetis_entered_by"],
            veterinary_document_id=row["veterinary_document_id"],
            created_at=row["created_at"],
        )
