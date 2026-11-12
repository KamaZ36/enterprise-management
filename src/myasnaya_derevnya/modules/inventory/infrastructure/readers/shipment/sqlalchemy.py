from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import (
    ShipmentDetail,
    ShipmentLineItem,
    ShipmentListItem,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.shipment.base import (
    ShipmentReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    SHIPMENT_LINES_TABLE,
    SHIPMENTS_TABLE,
)


class SQLAlchemyShipmentReader(ShipmentReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ShipmentListItem], int]:
        conditions = []
        if org_unit_ids is not None:
            conditions.append(SHIPMENTS_TABLE.c.org_unit_id.in_(org_unit_ids))

        if search:
            conditions.extend(
                or_(
                    SHIPMENTS_TABLE.c.number.ilike(
                        like_pattern(token), escape="\\"
                    ),
                    SHIPMENTS_TABLE.c.recipient.ilike(
                        like_pattern(token), escape="\\"
                    ),
                )
                for token in search.split()
            )

        total_documents = await self._session.scalar(
            select(func.count()).select_from(SHIPMENTS_TABLE).where(*conditions)
        )

        stmt = (
            select(
                SHIPMENTS_TABLE.c.id,
                SHIPMENTS_TABLE.c.number,
                SHIPMENTS_TABLE.c.org_unit_id,
                SHIPMENTS_TABLE.c.status,
                SHIPMENTS_TABLE.c.occurred_at,
                SHIPMENTS_TABLE.c.posted_at,
                SHIPMENTS_TABLE.c.recipient,
                func.count(SHIPMENT_LINES_TABLE.c.id).label("line_count"),
            )
            .select_from(
                SHIPMENTS_TABLE.outerjoin(
                    SHIPMENT_LINES_TABLE,
                    SHIPMENT_LINES_TABLE.c.shipment_id == SHIPMENTS_TABLE.c.id,
                )
            )
            .where(*conditions)
            .group_by(SHIPMENTS_TABLE.c.id)
            .order_by(
                SHIPMENTS_TABLE.c.occurred_at.desc(),
                SHIPMENTS_TABLE.c.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows], total_documents or 0

    async def get(self, shipment_id: UUID) -> ShipmentDetail | None:
        header = (
            (
                await self._session.execute(
                    select(SHIPMENTS_TABLE).where(SHIPMENTS_TABLE.c.id == shipment_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if header is None:
            return None

        lines = (
            (
                await self._session.execute(
                    select(SHIPMENT_LINES_TABLE)
                    .where(SHIPMENT_LINES_TABLE.c.shipment_id == shipment_id)
                    .order_by(SHIPMENT_LINES_TABLE.c.id)
                )
            )
            .mappings()
            .all()
        )

        return ShipmentDetail(
            id=header["id"],
            org_unit_id=header["org_unit_id"],
            status=header["status"],
            occurred_at=header["occurred_at"],
            posted_at=header["posted_at"],
            recipient=header["recipient"],
            comment=header["comment"],
            lines=[self._to_line_item(row) for row in lines],
            number=header["number"],
        )

    def _to_list_item(self, row: RowMapping) -> ShipmentListItem:
        return ShipmentListItem(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            number=row["number"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            recipient=row["recipient"],
            line_count=row["line_count"],
        )

    def _to_line_item(self, row: RowMapping) -> ShipmentLineItem:
        return ShipmentLineItem(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            lot_code=row["lot_code"],
        )
