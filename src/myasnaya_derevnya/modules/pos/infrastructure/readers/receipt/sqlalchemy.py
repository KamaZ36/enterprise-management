from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.application.dto import (
    PosReceiptDetail,
    PosReceiptLineItem,
    PosReceiptListItem,
)
from myasnaya_derevnya.modules.pos.infrastructure.readers.receipt.base import (
    PosReceiptReader,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import (
    POS_RECEIPT_LINES_TABLE,
    POS_RECEIPTS_TABLE,
    POS_SOURCES_TABLE,
)


class SQLAlchemyPosReceiptReader(PosReceiptReader):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        source_id: UUID | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        org_unit_ids: frozenset[UUID] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[PosReceiptListItem], int]:
        conditions = self._conditions(
            source_id=source_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            org_unit_ids=org_unit_ids,
        )

        stmt = (
            select(
                POS_RECEIPTS_TABLE,
                POS_SOURCES_TABLE.c.name.label("source_name"),
                self._line_count().label("line_count"),
                self._unmapped_count().label("unmapped_count"),
            )
            .join(
                POS_SOURCES_TABLE,
                POS_SOURCES_TABLE.c.id == POS_RECEIPTS_TABLE.c.source_id,
            )
            .where(*conditions)
            .order_by(
                POS_RECEIPTS_TABLE.c.occurred_at.desc(),
                POS_RECEIPTS_TABLE.c.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        rows = (await self._session.execute(stmt)).mappings().all()

        total = await self._session.scalar(
            select(func.count())
            .select_from(POS_RECEIPTS_TABLE)
            .where(*conditions)
        )

        return [self._to_list_item(row) for row in rows], int(total or 0)

    async def get(self, receipt_id: UUID) -> PosReceiptDetail | None:
        row = (
            (
                await self._session.execute(
                    select(
                        POS_RECEIPTS_TABLE,
                        POS_SOURCES_TABLE.c.name.label("source_name"),
                        self._line_count().label("line_count"),
                        self._unmapped_count().label("unmapped_count"),
                    )
                    .join(
                        POS_SOURCES_TABLE,
                        POS_SOURCES_TABLE.c.id == POS_RECEIPTS_TABLE.c.source_id,
                    )
                    .where(POS_RECEIPTS_TABLE.c.id == receipt_id)
                )
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        line_rows = (
            (
                await self._session.execute(
                    select(POS_RECEIPT_LINES_TABLE)
                    .where(POS_RECEIPT_LINES_TABLE.c.receipt_id == receipt_id)
                    .order_by(POS_RECEIPT_LINES_TABLE.c.line_number.asc())
                )
            )
            .mappings()
            .all()
        )

        item = self._to_list_item(row)

        return PosReceiptDetail(
            **asdict(item),
            subdivision_code=row["subdivision_code"],
            cashier=row["cashier"],
            shift=row["shift"],
            number=row["number"],
            fd_number=row["fd_number"],
            fp_number=row["fp_number"],
            fn_number=row["fn_number"],
            raw=row["raw"],
            lines=tuple(self._to_line_item(line) for line in line_rows),
        )

    def _line_count(self):
        return (
            select(func.count())
            .select_from(POS_RECEIPT_LINES_TABLE)
            .where(POS_RECEIPT_LINES_TABLE.c.receipt_id == POS_RECEIPTS_TABLE.c.id)
            .scalar_subquery()
        )

    def _unmapped_count(self):
        return (
            select(func.count())
            .select_from(POS_RECEIPT_LINES_TABLE)
            .where(
                POS_RECEIPT_LINES_TABLE.c.receipt_id == POS_RECEIPTS_TABLE.c.id,
                POS_RECEIPT_LINES_TABLE.c.mapping_status == "unmapped",
            )
            .scalar_subquery()
        )

    @staticmethod
    def _conditions(
        *,
        source_id: UUID | None,
        status: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        org_unit_ids: frozenset[UUID] | None,
    ) -> list:
        conditions = []

        if source_id is not None:
            conditions.append(POS_RECEIPTS_TABLE.c.source_id == source_id)
        if status is not None:
            conditions.append(POS_RECEIPTS_TABLE.c.status == status)
        if date_from is not None:
            conditions.append(POS_RECEIPTS_TABLE.c.occurred_at >= date_from)
        if date_to is not None:
            conditions.append(POS_RECEIPTS_TABLE.c.occurred_at <= date_to)
        if org_unit_ids is not None:
            conditions.append(POS_RECEIPTS_TABLE.c.org_unit_id.in_(org_unit_ids))

        return conditions

    @staticmethod
    def _to_list_item(row) -> PosReceiptListItem:
        return PosReceiptListItem(
            id=row["id"],
            source_id=row["source_id"],
            source_name=row["source_name"],
            external_guid=row["external_guid"],
            occurred_at=row["occurred_at"],
            kind=row["kind"],
            payment_kind=row["payment_kind"],
            total_kopecks=row["total_kopecks"],
            subdivision_name=row["subdivision_name"],
            status=row["status"],
            error=row["error"],
            line_count=row["line_count"],
            unmapped_count=row["unmapped_count"],
            posted_at=row["posted_at"],
            org_unit_id=row["org_unit_id"],
        )

    @staticmethod
    def _to_line_item(row) -> PosReceiptLineItem:
        return PosReceiptLineItem(
            id=row["id"],
            line_number=row["line_number"],
            external_guid=row["external_guid"],
            product_guid=row["product_guid"],
            product_name=row["product_name"],
            unit=row["unit"],
            quantity=row["quantity"],
            unit_factor=row["unit_factor"],
            price_kopecks=row["price_kopecks"],
            amount_kopecks=row["amount_kopecks"],
            discount_kopecks=row["discount_kopecks"],
            barcode=row["barcode"],
            mark_code=row["mark_code"],
            nomenclature_id=row["nomenclature_id"],
            mapping_status=row["mapping_status"],
            mapping_error=row["mapping_error"],
        )
