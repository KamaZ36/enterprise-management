from uuid import UUID

from sqlalchemy import RowMapping, delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.inventory.domain.entities.shipment import (
    Shipment,
    ShipmentLine,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.shipment.base import (
    ShipmentRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    SHIPMENT_LINES_TABLE,
    SHIPMENTS_TABLE,
)


class SQLAlchemyShipmentRepository(ShipmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, shipment: Shipment) -> None:
        await self._session.execute(
            insert(SHIPMENTS_TABLE).values(
                id=shipment.id,
                status=shipment.status.value,
                number=shipment.number,
                occurred_at=shipment.occurred_at,
                org_unit_id=shipment.org_unit_id,
                recipient=shipment.recipient,
                comment=shipment.comment,
                created_by=shipment.created_by,
                created_at=shipment.created_at,
                posted_at=shipment.posted_at,
            )
        )

        await self._insert_lines(shipment)

    async def save(self, shipment: Shipment) -> None:
        await self._session.execute(
            update(SHIPMENTS_TABLE)
            .where(SHIPMENTS_TABLE.c.id == shipment.id)
            .values(
                status=shipment.status.value,
                posted_at=shipment.posted_at,
                occurred_at=shipment.occurred_at,
                recipient=shipment.recipient,
                comment=shipment.comment,
            )
        )

        await self._session.execute(
            delete(SHIPMENT_LINES_TABLE).where(
                SHIPMENT_LINES_TABLE.c.shipment_id == shipment.id
            )
        )

        await self._insert_lines(shipment)

    async def _insert_lines(self, shipment: Shipment) -> None:
        lines = shipment.lines
        if not lines:
            return

        await self._session.execute(
            insert(SHIPMENT_LINES_TABLE).values(
                [
                    {
                        "id": line.id,
                        "shipment_id": shipment.id,
                        "nomenclature_id": line.nomenclature_id,
                        "lot_id": line.lot_id,
                        "lot_code": line.lot_code,
                        "quantity": line.quantity,
                    }
                    for line in lines
                ]
            )
        )

    async def get_by_id(self, shipment_id: UUID) -> Shipment | None:
        stmt = select(SHIPMENTS_TABLE).where(SHIPMENTS_TABLE.c.id == shipment_id)
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(SHIPMENT_LINES_TABLE)
            .where(SHIPMENT_LINES_TABLE.c.shipment_id == shipment_id)
            .order_by(SHIPMENT_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return self._to_entity(row, [self._to_line(line) for line in line_rows])

    async def delete(self, shipment_id: UUID) -> None:
        await self._session.execute(
            delete(SHIPMENTS_TABLE).where(SHIPMENTS_TABLE.c.id == shipment_id)
        )

    def _to_entity(self, row: RowMapping, lines: list[ShipmentLine]) -> Shipment:
        return Shipment(
            id=row["id"],
            status=DocumentStatus(row["status"]),
            number=row["number"],
            occurred_at=row["occurred_at"],
            org_unit_id=row["org_unit_id"],
            recipient=row["recipient"],
            comment=row["comment"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            posted_at=row["posted_at"],
            lines=lines,
        )

    def _to_line(self, row: RowMapping) -> ShipmentLine:
        return ShipmentLine(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            lot_id=row["lot_id"],
            lot_code=row["lot_code"],
        )
