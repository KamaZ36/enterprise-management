from uuid import UUID

from sqlalchemy import RowMapping, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.receipt import (
    Receipt,
    ReceiptLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.base import (
    ReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    RECEIPT_LINES_TABLE,
    RECEIPTS_TABLE,
)


class SQLAlchemyReceiptRepository(ReceiptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, receipt: Receipt) -> None:
        await self._session.execute(
            insert(RECEIPTS_TABLE).values(
                id=receipt.id,
                status=receipt.status.value,
                occurred_at=receipt.occurred_at,
                warehouse_id=receipt.warehouse_id,
                supplier_name=receipt.supplier_name,
                supplier_document_number=receipt.supplier_document_number,
                comment=receipt.comment,
                created_by=receipt.created_by,
                created_at=receipt.created_at,
                posted_at=receipt.posted_at,
            )
        )

        lines = receipt.lines
        if lines:
            await self._session.execute(
                insert(RECEIPT_LINES_TABLE).values(
                    [
                        {
                            "id": line.id,
                            "receipt_id": receipt.id,
                            "nomenclature_id": line.nomenclature_id,
                            "lot_id": line.lot_id,
                            "lot_code": line.lot_code,
                            "expires_at": line.expires_at,
                            "quantity": line.quantity,
                            "unit_cost": line.unit_cost,
                            "total_cost": line.total_cost.kopecks,
                        }
                        for line in lines
                    ]
                )
            )

    async def save(self, receipt: Receipt) -> None:
        await self._session.execute(
            update(RECEIPTS_TABLE)
            .where(RECEIPTS_TABLE.c.id == receipt.id)
            .values(status=receipt.status.value, posted_at=receipt.posted_at)
        )

    async def get_by_id(self, receipt_id: UUID) -> Receipt | None:
        stmt = select(RECEIPTS_TABLE).where(RECEIPTS_TABLE.c.id == receipt_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(RECEIPT_LINES_TABLE)
            .where(RECEIPT_LINES_TABLE.c.receipt_id == receipt_id)
            .order_by(RECEIPT_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return self._to_entity(row, [self._to_line(line) for line in line_rows])

    def _to_entity(self, row: RowMapping, lines: list[ReceiptLine]) -> Receipt:
        return Receipt(
            id=row["id"],
            status=DocumentStatus(row["status"]),
            occurred_at=row["occurred_at"],
            warehouse_id=row["warehouse_id"],
            supplier_name=row["supplier_name"],
            supplier_document_number=row["supplier_document_number"],
            comment=row["comment"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            posted_at=row["posted_at"],
            lines=lines,
        )

    def _to_line(self, row: RowMapping) -> ReceiptLine:
        return ReceiptLine(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            unit_cost=row["unit_cost"],
            total_cost=Money(kopecks=row["total_cost"]),
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
            expires_at=row["expires_at"],
        )
