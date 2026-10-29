from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosLineMappingStatus,
    PosReceipt,
    PosReceiptKind,
    PosReceiptLine,
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.tables import (
    POS_RECEIPT_LINES_TABLE,
    POS_RECEIPTS_TABLE,
)

TERMINAL_STATUSES = (
    PosReceiptStatus.POSTED.value,
    PosReceiptStatus.IGNORED.value,
)


class SQLAlchemyPosReceiptRepository(PosReceiptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, receipt: PosReceipt) -> bool:
        stmt = (
            pg_insert(POS_RECEIPTS_TABLE)
            .values(**self._receipt_values(receipt))
            .on_conflict_do_nothing(constraint="uq_pos_receipts_source_guid")
            .returning(POS_RECEIPTS_TABLE.c.id)
        )
        inserted = (await self._session.execute(stmt)).scalar_one_or_none()
        if inserted is None:
            return False

        if receipt.lines:
            await self._session.execute(
                insert(POS_RECEIPT_LINES_TABLE).values(
                    [self._line_values(line) for line in receipt.lines]
                )
            )

        return True

    async def get_by_id(self, receipt_id: UUID) -> PosReceipt | None:
        row = (
            (
                await self._session.execute(
                    select(POS_RECEIPTS_TABLE).where(
                        POS_RECEIPTS_TABLE.c.id == receipt_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        return await self._load(row)

    async def get_by_source_guid(
        self, source_id: UUID, external_guid: str
    ) -> PosReceipt | None:
        row = (
            (
                await self._session.execute(
                    select(POS_RECEIPTS_TABLE).where(
                        POS_RECEIPTS_TABLE.c.source_id == source_id,
                        POS_RECEIPTS_TABLE.c.external_guid == external_guid,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            return None

        return await self._load(row)

    async def save(self, receipt: PosReceipt) -> None:
        await self._session.execute(
            update(POS_RECEIPTS_TABLE)
            .where(POS_RECEIPTS_TABLE.c.id == receipt.id)
            .values(
                status=receipt.status.value,
                error=receipt.error,
                posted_at=receipt.posted_at,
                updated_at=receipt.updated_at,
            )
        )

    async def apply_mapping(
        self,
        *,
        source_id: UUID,
        doka_product_guid: str,
        nomenclature_id: UUID,
        unit_factor,
    ) -> list[UUID]:
        target_receipts = select(POS_RECEIPTS_TABLE.c.id).where(
            POS_RECEIPTS_TABLE.c.source_id == source_id,
            POS_RECEIPTS_TABLE.c.status.not_in(TERMINAL_STATUSES),
        )

        affected = (
            await self._session.execute(
                select(POS_RECEIPT_LINES_TABLE.c.receipt_id)
                .where(
                    POS_RECEIPT_LINES_TABLE.c.receipt_id.in_(target_receipts),
                    POS_RECEIPT_LINES_TABLE.c.product_guid == doka_product_guid,
                )
                .distinct()
            )
        ).scalars().all()

        receipt_ids = list(affected)
        if not receipt_ids:
            return []

        await self._session.execute(
            update(POS_RECEIPT_LINES_TABLE)
            .where(
                POS_RECEIPT_LINES_TABLE.c.receipt_id.in_(receipt_ids),
                POS_RECEIPT_LINES_TABLE.c.product_guid == doka_product_guid,
            )
            .values(
                nomenclature_id=nomenclature_id,
                unit_factor=unit_factor,
                mapping_status=PosLineMappingStatus.MAPPED.value,
                mapping_error=None,
            )
        )

        return receipt_ids

    async def pending_receipt_ids(
        self, *, statuses: Iterable[str], limit: int
    ) -> list[UUID]:
        result = await self._session.execute(
            select(POS_RECEIPTS_TABLE.c.id)
            .where(POS_RECEIPTS_TABLE.c.status.in_(list(statuses)))
            .order_by(POS_RECEIPTS_TABLE.c.occurred_at.asc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def _load(self, row) -> PosReceipt:
        line_rows = (
            (
                await self._session.execute(
                    select(POS_RECEIPT_LINES_TABLE)
                    .where(POS_RECEIPT_LINES_TABLE.c.receipt_id == row["id"])
                    .order_by(POS_RECEIPT_LINES_TABLE.c.line_number.asc())
                )
            )
            .mappings()
            .all()
        )

        return self._to_receipt(row, line_rows)

    @staticmethod
    def _receipt_values(receipt: PosReceipt) -> dict:
        return {
            "id": receipt.id,
            "source_id": receipt.source_id,
            "agent_id": receipt.agent_id,
            "batch_id": receipt.batch_id,
            "external_guid": receipt.external_guid,
            "occurred_at": receipt.occurred_at,
            "kind": receipt.kind.value,
            "payment_kind": receipt.payment_kind,
            "total_kopecks": receipt.total_kopecks,
            "subdivision_code": receipt.subdivision_code,
            "subdivision_name": receipt.subdivision_name,
            "cashier": receipt.cashier,
            "shift": receipt.shift,
            "number": receipt.number,
            "fd_number": receipt.fd_number,
            "fp_number": receipt.fp_number,
            "fn_number": receipt.fn_number,
            "org_unit_id": receipt.org_unit_id,
            "status": receipt.status.value,
            "error": receipt.error,
            "posted_at": receipt.posted_at,
            "raw": receipt.raw,
            "created_at": receipt.created_at,
            "updated_at": receipt.updated_at,
        }

    @staticmethod
    def _line_values(line: PosReceiptLine) -> dict:
        return {
            "id": line.id,
            "receipt_id": line.receipt_id,
            "line_number": line.line_number,
            "external_guid": line.external_guid,
            "product_guid": line.product_guid,
            "product_name": line.product_name,
            "unit": line.unit,
            "quantity": line.quantity,
            "unit_factor": line.unit_factor,
            "price_kopecks": line.price_kopecks,
            "amount_kopecks": line.amount_kopecks,
            "discount_kopecks": line.discount_kopecks,
            "barcode": line.barcode,
            "mark_code": line.mark_code,
            "nomenclature_id": line.nomenclature_id,
            "mapping_status": line.mapping_status.value,
            "mapping_error": line.mapping_error,
            "raw": line.raw,
            "created_at": line.created_at,
        }

    @staticmethod
    def _to_receipt(row, line_rows) -> PosReceipt:
        return PosReceipt(
            id=row["id"],
            source_id=row["source_id"],
            agent_id=row["agent_id"],
            batch_id=row["batch_id"],
            external_guid=row["external_guid"],
            occurred_at=row["occurred_at"],
            kind=PosReceiptKind(row["kind"]),
            payment_kind=row["payment_kind"],
            total_kopecks=row["total_kopecks"],
            subdivision_code=row["subdivision_code"],
            subdivision_name=row["subdivision_name"],
            cashier=row["cashier"],
            shift=row["shift"],
            number=row["number"],
            fd_number=row["fd_number"],
            fp_number=row["fp_number"],
            fn_number=row["fn_number"],
            org_unit_id=row["org_unit_id"],
            status=PosReceiptStatus(row["status"]),
            error=row["error"],
            posted_at=row["posted_at"],
            raw=row["raw"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            lines=[SQLAlchemyPosReceiptRepository._to_line(line) for line in line_rows],
        )

    @staticmethod
    def _to_line(row) -> PosReceiptLine:
        return PosReceiptLine(
            id=row["id"],
            receipt_id=row["receipt_id"],
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
            mapping_status=PosLineMappingStatus(row["mapping_status"]),
            mapping_error=row["mapping_error"],
            raw=row["raw"],
            created_at=row["created_at"],
        )
