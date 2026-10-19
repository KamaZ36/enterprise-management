from uuid import UUID

from sqlalchemy import RowMapping, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.inventory_count import (
    InventoryCount,
    InventoryCountLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.base import (
    InventoryCountRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    INVENTORY_COUNT_LINES_TABLE,
    INVENTORY_COUNTS_TABLE,
)


class SQLAlchemyInventoryCountRepository(InventoryCountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, inventory_count: InventoryCount) -> None:
        await self._session.execute(
            insert(INVENTORY_COUNTS_TABLE).values(
                id=inventory_count.id,
                status=inventory_count.status.value,
                occurred_at=inventory_count.occurred_at,
                org_unit_id=inventory_count.org_unit_id,
                comment=inventory_count.comment,
                created_by=inventory_count.created_by,
                created_at=inventory_count.created_at,
                posted_at=inventory_count.posted_at,
            )
        )

        await self._insert_lines(inventory_count)

    async def save(self, inventory_count: InventoryCount) -> None:
        await self._session.execute(
            update(INVENTORY_COUNTS_TABLE)
            .where(INVENTORY_COUNTS_TABLE.c.id == inventory_count.id)
            .values(
                status=inventory_count.status.value,
                posted_at=inventory_count.posted_at,
                occurred_at=inventory_count.occurred_at,
                comment=inventory_count.comment,
            )
        )

        await self._session.execute(
            delete(INVENTORY_COUNT_LINES_TABLE).where(
                INVENTORY_COUNT_LINES_TABLE.c.inventory_count_id
                == inventory_count.id
            )
        )

        await self._insert_lines(inventory_count)

    async def get_by_id(self, inventory_count_id: UUID) -> InventoryCount | None:
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

        return self._to_entity(row, [self._to_line(line) for line in line_rows])

    async def delete(self, inventory_count_id: UUID) -> None:
        await self._session.execute(
            delete(INVENTORY_COUNTS_TABLE).where(
                INVENTORY_COUNTS_TABLE.c.id == inventory_count_id
            )
        )

    async def _insert_lines(self, inventory_count: InventoryCount) -> None:
        lines = inventory_count.lines
        if not lines:
            return

        await self._session.execute(
            insert(INVENTORY_COUNT_LINES_TABLE).values(
                [
                    {
                        "id": line.id,
                        "inventory_count_id": inventory_count.id,
                        "nomenclature_id": line.nomenclature_id,
                        "lot_id": line.lot_id,
                        "lot_code": line.lot_code,
                        "counted_quantity": line.counted_quantity,
                    }
                    for line in lines
                ]
            )
        )

    def _to_entity(
        self, row: RowMapping, lines: list[InventoryCountLine]
    ) -> InventoryCount:
        return InventoryCount(
            id=row["id"],
            status=DocumentStatus(row["status"]),
            occurred_at=row["occurred_at"],
            org_unit_id=row["org_unit_id"],
            comment=row["comment"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            posted_at=row["posted_at"],
            lines=lines,
        )

    def _to_line(self, row: RowMapping) -> InventoryCountLine:
        return InventoryCountLine(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            counted_quantity=row["counted_quantity"],
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
        )
