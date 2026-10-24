from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.fiscal.application.dto import (
    OfdReceiptDetail,
    OfdReceiptLineItem,
    OfdReceiptListItem,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.readers.ofd_receipt.base import (
    OfdReceiptReader,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.tables import (
    OFD_RECEIPT_LINES_TABLE,
    OFD_RECEIPTS_TABLE,
)


class SQLAlchemyOfdReceiptReader(OfdReceiptReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        status: str | None,
        reg_number: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        org_unit_ids: frozenset[UUID] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[OfdReceiptListItem], int]:
        conditions = self._conditions(
            status=status,
            reg_number=reg_number,
            date_from=date_from,
            date_to=date_to,
            org_unit_ids=org_unit_ids,
        )

        line_count = (
            select(func.count())
            .select_from(OFD_RECEIPT_LINES_TABLE)
            .where(OFD_RECEIPT_LINES_TABLE.c.receipt_id == OFD_RECEIPTS_TABLE.c.id)
            .scalar_subquery()
        )
        unmapped_count = (
            select(func.count())
            .select_from(OFD_RECEIPT_LINES_TABLE)
            .where(
                OFD_RECEIPT_LINES_TABLE.c.receipt_id == OFD_RECEIPTS_TABLE.c.id,
                OFD_RECEIPT_LINES_TABLE.c.mapping_status != "mapped",
            )
            .scalar_subquery()
        )

        result = await self._session.execute(
            select(
                OFD_RECEIPTS_TABLE,
                line_count.label("line_count"),
                unmapped_count.label("unmapped_count"),
            )
            .where(*conditions)
            .order_by(OFD_RECEIPTS_TABLE.c.doc_datetime.desc())
            .limit(limit)
            .offset(offset)
        )

        total_result = await self._session.execute(
            select(func.count())
            .select_from(OFD_RECEIPTS_TABLE)
            .where(*conditions)
        )

        items = [
            OfdReceiptListItem(
                id=row["id"],
                reg_number=row["reg_number"],
                doc_number=row["doc_number"],
                fiscal_sign=row["fiscal_sign"],
                doc_datetime=row["doc_datetime"],
                operation_type=row["operation_type"],
                status=row["status"],
                total_kopecks=row["total_kopecks"],
                line_count=row["line_count"] or 0,
                unmapped_count=row["unmapped_count"] or 0,
                org_unit_id=row["org_unit_id"],
                error=row["error"],
                posted_at=row["posted_at"],
            )
            for row in result.mappings().all()
        ]

        return items, total_result.scalar_one()

    async def get(self, receipt_id: UUID) -> OfdReceiptDetail | None:
        result = await self._session.execute(
            select(OFD_RECEIPTS_TABLE).where(OFD_RECEIPTS_TABLE.c.id == receipt_id)
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None

        lines_result = await self._session.execute(
            select(OFD_RECEIPT_LINES_TABLE)
            .where(OFD_RECEIPT_LINES_TABLE.c.receipt_id == receipt_id)
            .order_by(OFD_RECEIPT_LINES_TABLE.c.line_number)
        )
        lines = tuple(
            OfdReceiptLineItem(
                id=line["id"],
                line_number=line["line_number"],
                name=line["name"],
                barcode=line["barcode"],
                quantity=line["quantity"],
                unit=line["unit"],
                price_kopecks=line["price_kopecks"],
                total_kopecks=line["total_kopecks"],
                mapping_status=line["mapping_status"],
                nomenclature_id=line["nomenclature_id"],
                mapping_error=line["mapping_error"],
            )
            for line in lines_result.mappings().all()
        )

        return OfdReceiptDetail(
            id=row["id"],
            reg_number=row["reg_number"],
            doc_number=row["doc_number"],
            fiscal_sign=row["fiscal_sign"],
            doc_datetime=row["doc_datetime"],
            operation_type=row["operation_type"],
            status=row["status"],
            total_kopecks=row["total_kopecks"],
            line_count=len(lines),
            unmapped_count=sum(
                1 for line in lines if line.mapping_status != "mapped"
            ),
            org_unit_id=row["org_unit_id"],
            error=row["error"],
            posted_at=row["posted_at"],
            inn=row["inn"],
            fn_number=row["fn_number"],
            cash_kopecks=row["cash_kopecks"],
            ecash_kopecks=row["ecash_kopecks"],
            is_correction=row["is_correction"],
            is_bso=row["is_bso"],
            raw=row["raw"],
            lines=lines,
        )

    @staticmethod
    def _conditions(
        *,
        status: str | None,
        reg_number: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        org_unit_ids: frozenset[UUID] | None,
    ) -> list:
        conditions: list = []
        if status:
            conditions.append(OFD_RECEIPTS_TABLE.c.status == status)
        if reg_number:
            conditions.append(OFD_RECEIPTS_TABLE.c.reg_number == reg_number)
        if date_from is not None:
            conditions.append(OFD_RECEIPTS_TABLE.c.doc_datetime >= date_from)
        if date_to is not None:
            conditions.append(OFD_RECEIPTS_TABLE.c.doc_datetime <= date_to)
        if org_unit_ids is not None:
            conditions.append(OFD_RECEIPTS_TABLE.c.org_unit_id.in_(org_unit_ids))
        return conditions
