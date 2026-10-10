from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.write_off import (
    WriteOff,
    WriteOffLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    WRITE_OFF_LINES_TABLE,
    WRITE_OFFS_TABLE,
)


class SQLAlchemyWriteOffRepository(WriteOffRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, write_off: WriteOff) -> None:
        await self._session.execute(
            insert(WRITE_OFFS_TABLE).values(
                id=write_off.id,
                status=write_off.status.value,
                occurred_at=write_off.occurred_at,
                warehouse_id=write_off.warehouse_id,
                reason=write_off.reason,
                comment=write_off.comment,
                created_by=write_off.created_by,
                created_at=write_off.created_at,
                posted_at=write_off.posted_at,
            )
        )

        lines = write_off.lines
        if lines:
            await self._session.execute(
                insert(WRITE_OFF_LINES_TABLE).values(
                    [
                        {
                            "id": line.id,
                            "write_off_id": write_off.id,
                            "nomenclature_id": line.nomenclature_id,
                            "lot_id": line.lot_id,
                            "lot_code": line.lot_code,
                            "quantity": line.quantity,
                        }
                        for line in lines
                    ]
                )
            )

    async def save(self, write_off: WriteOff) -> None:
        await self._session.execute(
            update(WRITE_OFFS_TABLE)
            .where(WRITE_OFFS_TABLE.c.id == write_off.id)
            .values(status=write_off.status.value, posted_at=write_off.posted_at)
        )

    async def get_by_id(self, write_off_id: UUID) -> WriteOff | None:
        stmt = select(WRITE_OFFS_TABLE).where(WRITE_OFFS_TABLE.c.id == write_off_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(WRITE_OFF_LINES_TABLE)
            .where(WRITE_OFF_LINES_TABLE.c.write_off_id == write_off_id)
            .order_by(WRITE_OFF_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return self._to_entity(row, [self._to_line(line) for line in line_rows])

    def _to_entity(self, row: RowMapping, lines: list[WriteOffLine]) -> WriteOff:
        return WriteOff(
            id=row["id"],
            status=DocumentStatus(row["status"]),
            occurred_at=row["occurred_at"],
            warehouse_id=row["warehouse_id"],
            reason=row["reason"],
            comment=row["comment"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            posted_at=row["posted_at"],
            lines=lines,
        )

    def _to_line(self, row: RowMapping) -> WriteOffLine:
        return WriteOffLine(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
        )
