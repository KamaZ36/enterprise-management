from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.catalog.application.dto import StopListItem
from myasnaya_derevnya.modules.catalog.infrastructure.readers.stop_list.base import (
    StopListReader,
)
from myasnaya_derevnya.modules.catalog.infrastructure.tables import (
    NOMENCLATURES_TABLE,
    STOP_LIST_ENTRIES_TABLE,
)


class SQLAlchemyStopListReader(StopListReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_org_unit(self, org_unit_id: UUID) -> list[StopListItem]:
        stmt = (
            select(
                STOP_LIST_ENTRIES_TABLE.c.nomenclature_id,
                NOMENCLATURES_TABLE.c.name,
                NOMENCLATURES_TABLE.c.sku,
                STOP_LIST_ENTRIES_TABLE.c.created_by,
                STOP_LIST_ENTRIES_TABLE.c.created_at,
            )
            .select_from(
                STOP_LIST_ENTRIES_TABLE.join(
                    NOMENCLATURES_TABLE,
                    NOMENCLATURES_TABLE.c.id
                    == STOP_LIST_ENTRIES_TABLE.c.nomenclature_id,
                )
            )
            .where(STOP_LIST_ENTRIES_TABLE.c.org_unit_id == org_unit_id)
            .order_by(NOMENCLATURES_TABLE.c.name.asc())
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [
            StopListItem(
                nomenclature_id=row["nomenclature_id"],
                nomenclature_name=row["name"],
                sku=row["sku"],
                created_by=row["created_by"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    async def stopped_nomenclature_ids(
        self, org_unit_id: UUID, nomenclature_ids: Iterable[UUID]
    ) -> set[UUID]:
        ids = list(nomenclature_ids)
        if not ids:
            return set()

        stmt = select(STOP_LIST_ENTRIES_TABLE.c.nomenclature_id).where(
            STOP_LIST_ENTRIES_TABLE.c.org_unit_id == org_unit_id,
            STOP_LIST_ENTRIES_TABLE.c.nomenclature_id.in_(ids),
        )
        rows = (await self._session.execute(stmt)).all()

        return {row[0] for row in rows}
