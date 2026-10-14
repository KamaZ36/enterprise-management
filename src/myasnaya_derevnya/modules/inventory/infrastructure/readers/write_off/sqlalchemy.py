from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import (
    WriteOffDetail,
    WriteOffLineItem,
    WriteOffListItem,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.write_off.base import (
    WriteOffReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    WAREHOUSES_TABLE,
    WRITE_OFF_LINES_TABLE,
    WRITE_OFFS_TABLE,
)


class SQLAlchemyWriteOffReader(WriteOffReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        warehouse_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[WriteOffListItem], int]:
        conditions = []
        if warehouse_ids is not None:
            conditions.append(WRITE_OFFS_TABLE.c.warehouse_id.in_(warehouse_ids))

        if search:
            conditions.extend(
                or_(
                    WRITE_OFFS_TABLE.c.reason.ilike(like_pattern(token), escape="\\"),
                )
                for token in search.split()
            )

        total_documents = await self._session.scalar(
            select(func.count()).select_from(WRITE_OFFS_TABLE).where(*conditions)
        )

        stmt = (
            select(
                WRITE_OFFS_TABLE.c.id,
                WRITE_OFFS_TABLE.c.warehouse_id,
                WRITE_OFFS_TABLE.c.status,
                WRITE_OFFS_TABLE.c.occurred_at,
                WRITE_OFFS_TABLE.c.posted_at,
                WRITE_OFFS_TABLE.c.reason,
                func.count(WRITE_OFF_LINES_TABLE.c.id).label("line_count"),
            )
            .select_from(
                WRITE_OFFS_TABLE.outerjoin(
                    WRITE_OFF_LINES_TABLE,
                    WRITE_OFF_LINES_TABLE.c.write_off_id == WRITE_OFFS_TABLE.c.id,
                )
            )
            .where(*conditions)
            .group_by(WRITE_OFFS_TABLE.c.id)
            .order_by(
                WRITE_OFFS_TABLE.c.occurred_at.desc(),
                WRITE_OFFS_TABLE.c.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows], total_documents or 0

    async def get(self, write_off_id: UUID) -> WriteOffDetail | None:
        header = (
            (
                await self._session.execute(
                    select(
                        WRITE_OFFS_TABLE,
                        WAREHOUSES_TABLE.c.org_unit_id,
                    )
                    .select_from(
                        WRITE_OFFS_TABLE.outerjoin(
                            WAREHOUSES_TABLE,
                            WAREHOUSES_TABLE.c.id == WRITE_OFFS_TABLE.c.warehouse_id,
                        )
                    )
                    .where(WRITE_OFFS_TABLE.c.id == write_off_id)
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
                    select(WRITE_OFF_LINES_TABLE)
                    .where(WRITE_OFF_LINES_TABLE.c.write_off_id == write_off_id)
                    .order_by(WRITE_OFF_LINES_TABLE.c.id)
                )
            )
            .mappings()
            .all()
        )

        return WriteOffDetail(
            id=header["id"],
            warehouse_id=header["warehouse_id"],
            status=header["status"],
            occurred_at=header["occurred_at"],
            posted_at=header["posted_at"],
            reason=header["reason"],
            comment=header["comment"],
            lines=[self._to_line_item(row) for row in lines],
            org_unit_id=header["org_unit_id"],
        )

    def _to_list_item(self, row: RowMapping) -> WriteOffListItem:
        return WriteOffListItem(
            id=row["id"],
            warehouse_id=row["warehouse_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            reason=row["reason"],
            line_count=row["line_count"],
        )

    def _to_line_item(self, row: RowMapping) -> WriteOffLineItem:
        return WriteOffLineItem(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            lot_code=row["lot_code"],
        )
