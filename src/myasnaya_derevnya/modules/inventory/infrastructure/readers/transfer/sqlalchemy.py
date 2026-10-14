from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import (
    TransferDetail,
    TransferLineItem,
    TransferListItem,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.transfer.base import (
    TransferReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    TRANSFER_LINES_TABLE,
    TRANSFERS_TABLE,
    WAREHOUSES_TABLE,
)

FROM_WAREHOUSES = WAREHOUSES_TABLE.alias("from_warehouses")
TO_WAREHOUSES = WAREHOUSES_TABLE.alias("to_warehouses")


class SQLAlchemyTransferReader(TransferReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        warehouse_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[TransferListItem], int]:
        conditions = []
        if warehouse_ids is not None:
            conditions.append(
                or_(
                    TRANSFERS_TABLE.c.from_warehouse_id.in_(warehouse_ids),
                    TRANSFERS_TABLE.c.to_warehouse_id.in_(warehouse_ids),
                )
            )

        if search:
            conditions.extend(
                or_(
                    TRANSFERS_TABLE.c.comment.ilike(like_pattern(token), escape="\\"),
                )
                for token in search.split()
            )

        total_documents = await self._session.scalar(
            select(func.count()).select_from(TRANSFERS_TABLE).where(*conditions)
        )

        stmt = (
            select(
                TRANSFERS_TABLE.c.id,
                TRANSFERS_TABLE.c.from_warehouse_id,
                TRANSFERS_TABLE.c.to_warehouse_id,
                TRANSFERS_TABLE.c.status,
                TRANSFERS_TABLE.c.occurred_at,
                TRANSFERS_TABLE.c.posted_at,
                TRANSFERS_TABLE.c.comment,
                func.count(TRANSFER_LINES_TABLE.c.id).label("line_count"),
            )
            .outerjoin(
                TRANSFER_LINES_TABLE,
                TRANSFER_LINES_TABLE.c.transfer_id == TRANSFERS_TABLE.c.id,
            )
            .where(*conditions)
            .group_by(TRANSFERS_TABLE.c.id)
            .order_by(TRANSFERS_TABLE.c.occurred_at.desc(), TRANSFERS_TABLE.c.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows], int(total_documents or 0)

    async def get(self, transfer_id: UUID) -> TransferDetail | None:
        stmt = (
            select(
                TRANSFERS_TABLE,
                FROM_WAREHOUSES.c.org_unit_id.label("from_org_unit_id"),
                TO_WAREHOUSES.c.org_unit_id.label("to_org_unit_id"),
            )
            .select_from(
                TRANSFERS_TABLE.outerjoin(
                    FROM_WAREHOUSES,
                    FROM_WAREHOUSES.c.id == TRANSFERS_TABLE.c.from_warehouse_id,
                ).outerjoin(
                    TO_WAREHOUSES,
                    TO_WAREHOUSES.c.id == TRANSFERS_TABLE.c.to_warehouse_id,
                )
            )
            .where(TRANSFERS_TABLE.c.id == transfer_id)
        )
        row = (await self._session.execute(stmt)).mappings().one_or_none()

        if row is None:
            return None

        lines_stmt = (
            select(TRANSFER_LINES_TABLE)
            .where(TRANSFER_LINES_TABLE.c.transfer_id == transfer_id)
            .order_by(TRANSFER_LINES_TABLE.c.id.asc())
        )
        line_rows = (await self._session.execute(lines_stmt)).mappings().all()

        return TransferDetail(
            id=row["id"],
            from_warehouse_id=row["from_warehouse_id"],
            to_warehouse_id=row["to_warehouse_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            comment=row["comment"],
            lines=[self._to_line(line) for line in line_rows],
            org_unit_id=row["from_org_unit_id"],
            to_org_unit_id=row["to_org_unit_id"],
        )

    def _to_list_item(self, row: RowMapping) -> TransferListItem:
        return TransferListItem(
            id=row["id"],
            from_warehouse_id=row["from_warehouse_id"],
            to_warehouse_id=row["to_warehouse_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            comment=row["comment"],
            line_count=row["line_count"],
        )

    def _to_line(self, row: RowMapping) -> TransferLineItem:
        return TransferLineItem(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            lot_code=row["lot_code"],
        )
