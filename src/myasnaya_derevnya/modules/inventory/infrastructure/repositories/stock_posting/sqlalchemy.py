from sqlalchemy import insert
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
                warehouse_id=posting.warehouse_id,
                posted_at=posting.posted_at,
                posted_by=posting.posted_by,
            )
        )
