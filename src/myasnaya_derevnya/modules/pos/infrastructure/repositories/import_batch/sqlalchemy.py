from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.domain.entities.import_batch import PosImportBatch
from myasnaya_derevnya.modules.pos.infrastructure.repositories.import_batch.base import (
    PosImportBatchRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import (
    POS_IMPORT_BATCHES_TABLE,
)


class SQLAlchemyPosImportBatchRepository(PosImportBatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, batch: PosImportBatch) -> None:
        await self._session.execute(
            insert(POS_IMPORT_BATCHES_TABLE).values(
                id=batch.id,
                source_id=batch.source_id,
                agent_id=batch.agent_id,
                file_name=batch.file_name,
                file_sha256=batch.file_sha256,
                exported_at=batch.exported_at,
                received_at=batch.received_at,
                receipts_total=batch.receipts_total,
                receipts_created=batch.receipts_created,
                receipts_duplicate=batch.receipts_duplicate,
                receipts_posted=batch.receipts_posted,
                receipts_pending=batch.receipts_pending,
                receipts_failed=batch.receipts_failed,
                status=batch.status,
                error=batch.error,
                created_at=batch.created_at,
            )
        )

    async def save(self, batch: PosImportBatch) -> None:
        await self._session.execute(
            update(POS_IMPORT_BATCHES_TABLE)
            .where(POS_IMPORT_BATCHES_TABLE.c.id == batch.id)
            .values(
                receipts_created=batch.receipts_created,
                receipts_duplicate=batch.receipts_duplicate,
                receipts_posted=batch.receipts_posted,
                receipts_pending=batch.receipts_pending,
                receipts_failed=batch.receipts_failed,
                status=batch.status,
                error=batch.error,
            )
        )
