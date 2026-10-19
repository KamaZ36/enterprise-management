from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import (
    InventoryCountDetail,
    InventoryCountLineItem,
    InventoryCountListItem,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.inventory_count.base import (
    InventoryCountReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    INVENTORY_COUNT_LINES_TABLE,
    INVENTORY_COUNTS_TABLE,
)


class SQLAlchemyInventoryCountReader(InventoryCountReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[InventoryCountListItem], int]:
        conditions = []
        if org_unit_ids is not None:
            conditions.append(INVENTORY_COUNTS_TABLE.c.org_unit_id.in_(org_unit_ids))

        if search:
            conditions.extend(
                or_(
                    INVENTORY_COUNTS_TABLE.c.comment.ilike(
                        like_pattern(token), escape="\\"
                    ),
                )
                for token in search.split()
            )

        total_documents = await self._session.scalar(
            select(func.count())
            .select_from(INVENTORY_COUNTS_TABLE)
            .where(*conditions)
        )

        stmt = (
            select(
                INVENTORY_COUNTS_TABLE.c.id,
                INVENTORY_COUNTS_TABLE.c.org_unit_id,
                INVENTORY_COUNTS_TABLE.c.status,
                INVENTORY_COUNTS_TABLE.c.occurred_at,
                INVENTORY_COUNTS_TABLE.c.posted_at,
                INVENTORY_COUNTS_TABLE.c.comment,
                func.count(INVENTORY_COUNT_LINES_TABLE.c.id).label("line_count"),
            )
            .outerjoin(
                INVENTORY_COUNT_LINES_TABLE,
                INVENTORY_COUNT_LINES_TABLE.c.inventory_count_id
                == INVENTORY_COUNTS_TABLE.c.id,
            )
            .where(*conditions)
            .group_by(INVENTORY_COUNTS_TABLE.c.id)
            .order_by(
                INVENTORY_COUNTS_TABLE.c.occurred_at.desc(),
                INVENTORY_COUNTS_TABLE.c.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows], int(total_documents or 0)

    async def get(self, inventory_count_id: UUID) -> InventoryCountDetail | None:
        stmt = select(INVENTORY_COUNTS_TABLE).where(
            INVENTORY_COUNTS_TABLE.c.id == inventory_count_id
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(INVENTORY_COUNT_LINES_TABLE)
            .where(
                INVENTORY_COUNT_LINES_TABLE.c.inventory_count_id
                == inventory_count_id
            )
            .order_by(INVENTORY_COUNT_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return InventoryCountDetail(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            comment=row["comment"],
            lines=[self._to_line(line) for line in line_rows],
        )

    def _to_list_item(self, row: RowMapping) -> InventoryCountListItem:
        return InventoryCountListItem(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            comment=row["comment"],
            line_count=row["line_count"],
        )

    def _to_line(self, row: RowMapping) -> InventoryCountLineItem:
        return InventoryCountLineItem(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            counted_quantity=row["counted_quantity"],
            lot_code=row["lot_code"],
        )
