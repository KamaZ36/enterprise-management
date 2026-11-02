from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.domain.entities.stop_list_entry import (
    StopListEntry,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.stop_list.base import (
    StopListEntryRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    STOP_LIST_ENTRIES_TABLE,
)


class SQLAlchemyStopListEntryRepository(StopListEntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entry: StopListEntry) -> bool:
        result = await self._session.execute(
            insert(STOP_LIST_ENTRIES_TABLE)
            .values(
                id=entry.id,
                org_unit_id=entry.org_unit_id,
                nomenclature_id=entry.nomenclature_id,
                created_by=entry.created_by,
                created_at=entry.created_at,
            )
            .on_conflict_do_nothing(
                constraint="uq_stop_list_entries_org_unit_nomenclature",
            )
        )

        return bool(result.rowcount)

    async def delete(self, org_unit_id: UUID, nomenclature_id: UUID) -> bool:
        result = await self._session.execute(
            delete(STOP_LIST_ENTRIES_TABLE).where(
                STOP_LIST_ENTRIES_TABLE.c.org_unit_id == org_unit_id,
                STOP_LIST_ENTRIES_TABLE.c.nomenclature_id == nomenclature_id,
            )
        )

        return bool(result.rowcount)
