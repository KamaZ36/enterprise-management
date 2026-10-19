from uuid import UUID

from sqlalchemy import RowMapping, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    TRANSFER_LINES_TABLE,
    TRANSFERS_TABLE,
)


class SQLAlchemyTransferRepository(TransferRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, transfer: Transfer) -> None:
        await self._session.execute(
            insert(TRANSFERS_TABLE).values(
                id=transfer.id,
                status=transfer.status.value,
                occurred_at=transfer.occurred_at,
                from_org_unit_id=transfer.from_org_unit_id,
                to_org_unit_id=transfer.to_org_unit_id,
                comment=transfer.comment,
                created_by=transfer.created_by,
                created_at=transfer.created_at,
                posted_at=transfer.posted_at,
            )
        )

        lines = transfer.lines
        if lines:
            await self._session.execute(
                insert(TRANSFER_LINES_TABLE).values(
                    [
                        {
                            "id": line.id,
                            "transfer_id": transfer.id,
                            "nomenclature_id": line.nomenclature_id,
                            "lot_id": line.lot_id,
                            "lot_code": line.lot_code,
                            "quantity": line.quantity,
                        }
                        for line in lines
                    ]
                )
            )

    async def save(self, transfer: Transfer) -> None:
        await self._session.execute(
            update(TRANSFERS_TABLE)
            .where(TRANSFERS_TABLE.c.id == transfer.id)
            .values(
                status=transfer.status.value,
                posted_at=transfer.posted_at,
                occurred_at=transfer.occurred_at,
                comment=transfer.comment,
            )
        )

        await self._session.execute(
            delete(TRANSFER_LINES_TABLE).where(
                TRANSFER_LINES_TABLE.c.transfer_id == transfer.id
            )
        )

        lines = transfer.lines
        if lines:
            await self._session.execute(
                insert(TRANSFER_LINES_TABLE).values(
                    [
                        {
                            "id": line.id,
                            "transfer_id": transfer.id,
                            "nomenclature_id": line.nomenclature_id,
                            "lot_id": line.lot_id,
                            "lot_code": line.lot_code,
                            "quantity": line.quantity,
                        }
                        for line in lines
                    ]
                )
            )

    async def get_by_id(self, transfer_id: UUID) -> Transfer | None:
        stmt = select(TRANSFERS_TABLE).where(TRANSFERS_TABLE.c.id == transfer_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(TRANSFER_LINES_TABLE)
            .where(TRANSFER_LINES_TABLE.c.transfer_id == transfer_id)
            .order_by(TRANSFER_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return self._to_entity(row, [self._to_line(line) for line in line_rows])

    async def delete(self, transfer_id: UUID) -> None:
        await self._session.execute(
            delete(TRANSFERS_TABLE).where(TRANSFERS_TABLE.c.id == transfer_id)
        )

    def _to_entity(self, row: RowMapping, lines: list[TransferLine]) -> Transfer:
        return Transfer(
            id=row["id"],
            status=DocumentStatus(row["status"]),
            occurred_at=row["occurred_at"],
            from_org_unit_id=row["from_org_unit_id"],
            to_org_unit_id=row["to_org_unit_id"],
            comment=row["comment"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            posted_at=row["posted_at"],
            lines=lines,
        )

    def _to_line(self, row: RowMapping) -> TransferLine:
        return TransferLine(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
        )
