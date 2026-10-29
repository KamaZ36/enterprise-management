from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.application.dto import PosUnmappedProductItem
from myasnaya_derevnya.modules.pos.infrastructure.readers.product_map.base import (
    PosProductMapReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import (
    POS_PRODUCT_MAP_TABLE,
    POS_RECEIPT_LINES_TABLE,
    POS_RECEIPTS_TABLE,
)


class SQLAlchemyPosProductMapReader(PosProductMapReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def unmapped_products(
        self, source_id: UUID, *, limit: int = 200
    ) -> list[PosUnmappedProductItem]:
        mapped_guids = select(POS_PRODUCT_MAP_TABLE.c.doka_product_guid).where(
            POS_PRODUCT_MAP_TABLE.c.source_id == source_id,
            POS_PRODUCT_MAP_TABLE.c.is_active.is_(True),
        )

        stmt = (
            select(
                POS_RECEIPT_LINES_TABLE.c.product_guid,
                func.max(POS_RECEIPT_LINES_TABLE.c.product_name).label(
                    "product_name"
                ),
                func.max(POS_RECEIPT_LINES_TABLE.c.unit).label("unit"),
                func.count(func.distinct(POS_RECEIPT_LINES_TABLE.c.receipt_id)).label(
                    "receipts_count"
                ),
                func.max(POS_RECEIPTS_TABLE.c.occurred_at).label("last_seen_at"),
            )
            .join(
                POS_RECEIPTS_TABLE,
                POS_RECEIPTS_TABLE.c.id == POS_RECEIPT_LINES_TABLE.c.receipt_id,
            )
            .where(
                POS_RECEIPTS_TABLE.c.source_id == source_id,
                POS_RECEIPT_LINES_TABLE.c.nomenclature_id.is_(None),
                POS_RECEIPT_LINES_TABLE.c.product_guid.not_in(mapped_guids),
            )
            .group_by(POS_RECEIPT_LINES_TABLE.c.product_guid)
            .order_by(func.max(POS_RECEIPTS_TABLE.c.occurred_at).desc())
            .limit(limit)
        )

        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            PosUnmappedProductItem(
                product_guid=row["product_guid"],
                product_name=row["product_name"],
                unit=row["unit"],
                receipts_count=row["receipts_count"],
                last_seen_at=row["last_seen_at"],
            )
            for row in rows
        ]
