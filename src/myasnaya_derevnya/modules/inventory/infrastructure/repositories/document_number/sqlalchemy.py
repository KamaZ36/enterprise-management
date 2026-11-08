from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.document_number.base import (
    DocumentNumberRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    DOCUMENT_NUMBER_COUNTERS_TABLE,
)


class SQLAlchemyDocumentNumberRepository(DocumentNumberRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def next_sequence(
        self, document_type: DocumentType, year: int
    ) -> int:
        stmt = (
            pg_insert(DOCUMENT_NUMBER_COUNTERS_TABLE)
            .values(
                document_type=document_type.value,
                number_year=year,
                last_number=1,
            )
            .on_conflict_do_update(
                index_elements=[
                    DOCUMENT_NUMBER_COUNTERS_TABLE.c.document_type,
                    DOCUMENT_NUMBER_COUNTERS_TABLE.c.number_year,
                ],
                set_={
                    "last_number": DOCUMENT_NUMBER_COUNTERS_TABLE.c.last_number
                    + 1,
                },
            )
            .returning(DOCUMENT_NUMBER_COUNTERS_TABLE.c.last_number)
        )

        return int(await self._session.scalar(stmt))
