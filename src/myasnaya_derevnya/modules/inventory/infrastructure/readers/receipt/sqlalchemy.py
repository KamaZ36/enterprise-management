from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import RowMapping, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.core.database.search import like_pattern
from myasnaya_derevnya.modules.inventory.application.dto import (
    ReceiptDetail,
    ReceiptLineItem,
    ReceiptListItem,
)
from myasnaya_derevnya.modules.inventory.infrastructure.readers.receipt.base import (
    ReceiptReader,
)
from myasnaya_derevnya.modules.inventory.infrastructure.tables import (
    RECEIPT_LINES_TABLE,
    RECEIPTS_TABLE,
)


class SQLAlchemyReceiptReader(ReceiptReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        org_unit_ids: Sequence[UUID] | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ReceiptListItem], int]:
        conditions = []
        if org_unit_ids is not None:
            conditions.append(RECEIPTS_TABLE.c.org_unit_id.in_(org_unit_ids))

        if search:
            conditions.extend(
                or_(
                    RECEIPTS_TABLE.c.supplier_name.ilike(
                        like_pattern(token), escape="\\"
                    ),
                    RECEIPTS_TABLE.c.supplier_document_number.ilike(
                        like_pattern(token), escape="\\"
                    ),
                )
                for token in search.split()
            )

        total_documents = await self._session.scalar(
            select(func.count()).select_from(RECEIPTS_TABLE).where(*conditions)
        )

        stmt = (
            select(
                RECEIPTS_TABLE.c.id,
                RECEIPTS_TABLE.c.org_unit_id,
                RECEIPTS_TABLE.c.status,
                RECEIPTS_TABLE.c.occurred_at,
                RECEIPTS_TABLE.c.posted_at,
                RECEIPTS_TABLE.c.supplier_name,
                RECEIPTS_TABLE.c.supplier_document_number,
                func.count(RECEIPT_LINES_TABLE.c.id).label("line_count"),
                func.coalesce(func.sum(RECEIPT_LINES_TABLE.c.total_cost), 0).label(
                    "total_kopecks"
                ),
            )
            .select_from(
                RECEIPTS_TABLE.outerjoin(
                    RECEIPT_LINES_TABLE,
                    RECEIPT_LINES_TABLE.c.receipt_id == RECEIPTS_TABLE.c.id,
                )
            )
            .where(*conditions)
            .group_by(RECEIPTS_TABLE.c.id)
            .order_by(
                RECEIPTS_TABLE.c.occurred_at.desc(), RECEIPTS_TABLE.c.created_at.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).mappings().all()

        return [self._to_list_item(row) for row in rows], total_documents or 0

    async def get(self, receipt_id: UUID) -> ReceiptDetail | None:
        header = (
            (
                await self._session.execute(
                    select(RECEIPTS_TABLE).where(RECEIPTS_TABLE.c.id == receipt_id)
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
                    select(RECEIPT_LINES_TABLE)
                    .where(RECEIPT_LINES_TABLE.c.receipt_id == receipt_id)
                    .order_by(RECEIPT_LINES_TABLE.c.id)
                )
            )
            .mappings()
            .all()
        )

        return ReceiptDetail(
            id=header["id"],
            org_unit_id=header["org_unit_id"],
            status=header["status"],
            occurred_at=header["occurred_at"],
            posted_at=header["posted_at"],
            supplier_name=header["supplier_name"],
            supplier_document_number=header["supplier_document_number"],
            comment=header["comment"],
            lines=[self._to_line_item(row) for row in lines],
        )

    def _to_list_item(self, row: RowMapping) -> ReceiptListItem:
        return ReceiptListItem(
            id=row["id"],
            org_unit_id=row["org_unit_id"],
            status=row["status"],
            occurred_at=row["occurred_at"],
            posted_at=row["posted_at"],
            supplier_name=row["supplier_name"],
            supplier_document_number=row["supplier_document_number"],
            line_count=row["line_count"],
            total_kopecks=row["total_kopecks"],
        )

    def _to_line_item(self, row: RowMapping) -> ReceiptLineItem:
        return ReceiptLineItem(
            id=row["id"],
            nomenclature_id=row["nomenclature_id"],
            quantity=row["quantity"],
            unit_cost=row["unit_cost"],
            total_kopecks=row["total_cost"],
            lot_code=row["lot_code"],
            expires_at=row["expires_at"],
        )
