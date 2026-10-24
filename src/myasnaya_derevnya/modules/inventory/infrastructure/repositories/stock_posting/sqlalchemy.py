from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.stock_posting import (
    StockPosting,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.stock_posting.base import (
    StockPostingRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    STOCK_POSTINGS_TABLE,
)


class SQLAlchemyStockPostingRepository(StockPostingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, posting: StockPosting) -> None:
        await self._session.execute(
            insert(STOCK_POSTINGS_TABLE).values(
                id=posting.id,
                document_type=posting.document_type,
                document_id=posting.document_id,
                org_unit_id=posting.org_unit_id,
                posted_at=posting.posted_at,
                posted_by=posting.posted_by,
            )
        )

    async def exists(self, *, document_type: str, document_id: UUID) -> bool:
        result = await self._session.execute(
            select(STOCK_POSTINGS_TABLE.c.id).where(
                STOCK_POSTINGS_TABLE.c.document_type == document_type,
                STOCK_POSTINGS_TABLE.c.document_id == document_id,
            )
        )
        return result.scalar_one_or_none() is not None
