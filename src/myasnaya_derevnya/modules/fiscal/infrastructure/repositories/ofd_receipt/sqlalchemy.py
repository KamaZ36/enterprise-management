from uuid import UUID

from sqlalchemy import RowMapping, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_product_alias import (
    OfdProductAlias,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdLineMappingStatus,
    OfdReceipt,
    OfdReceiptLine,
    OfdReceiptStatus,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_sync_run import (
    OfdSyncRun,
)
from myasnaya_derevnya.modules.fiscal.domain.value_objects.barcode import (
    normalize_barcode,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.base import (
    OfdReceiptRepository,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.tables import (
    OFD_PRODUCT_ALIASES_TABLE,
    OFD_RECEIPT_LINES_TABLE,
    OFD_RECEIPTS_TABLE,
    OFD_SYNC_RUNS_TABLE,
)


class SQLAlchemyOfdReceiptRepository(OfdReceiptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_if_absent(self, receipt: OfdReceipt) -> bool:
        stmt = (
            pg_insert(OFD_RECEIPTS_TABLE)
            .values(
                id=receipt.id,
                inn=receipt.inn,
                reg_number=receipt.reg_number,
                fn_number=receipt.fn_number,
                doc_number=receipt.doc_number,
                fiscal_sign=receipt.fiscal_sign,
                raw_id=receipt.raw_id,
                doc_datetime=receipt.doc_datetime,
                c_date_utc=receipt.c_date_utc,
                operation_type=receipt.operation_type,
                is_correction=receipt.is_correction,
                is_bso=receipt.is_bso,
                total_kopecks=receipt.total_kopecks,
                cash_kopecks=receipt.cash_kopecks,
                ecash_kopecks=receipt.ecash_kopecks,
                org_unit_id=receipt.org_unit_id,
                status=receipt.status.value,
                error=receipt.error,
                posted_at=receipt.posted_at,
                posted_by=receipt.posted_by,
                raw=receipt.raw,
                created_at=receipt.created_at,
                updated_at=receipt.updated_at,
            )
            .on_conflict_do_nothing(constraint="uq_ofd_receipts_identity")
            .returning(OFD_RECEIPTS_TABLE.c.id)
        )
        result = await self._session.execute(stmt)
        if result.scalar_one_or_none() is None:
            return False

        lines = receipt.lines
        if lines:
            await self._session.execute(
                insert(OFD_RECEIPT_LINES_TABLE).values(
                    [self._line_values(line) for line in lines]
                )
            )

        return True

    async def get_by_id(self, receipt_id: UUID) -> OfdReceipt | None:
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
        lines = [self._to_line(item) for item in lines_result.mappings().all()]
        return self._to_receipt(row, lines)

    async def get_by_line_id(self, line_id: UUID) -> OfdReceipt | None:
        result = await self._session.execute(
            select(OFD_RECEIPT_LINES_TABLE.c.receipt_id).where(
                OFD_RECEIPT_LINES_TABLE.c.id == line_id
            )
        )
        receipt_id = result.scalar_one_or_none()
        if receipt_id is None:
            return None

        return await self.get_by_id(receipt_id)

    async def save(self, receipt: OfdReceipt) -> None:
        await self._session.execute(
            update(OFD_RECEIPTS_TABLE)
            .where(OFD_RECEIPTS_TABLE.c.id == receipt.id)
            .values(
                org_unit_id=receipt.org_unit_id,
                status=receipt.status.value,
                error=receipt.error,
                posted_at=receipt.posted_at,
                posted_by=receipt.posted_by,
                updated_at=receipt.updated_at,
            )
        )

    async def save_line(self, line: OfdReceiptLine) -> None:
        await self._session.execute(
            update(OFD_RECEIPT_LINES_TABLE)
            .where(OFD_RECEIPT_LINES_TABLE.c.id == line.id)
            .values(
                nomenclature_id=line.nomenclature_id,
                mapping_status=line.mapping_status.value,
                mapping_error=line.mapping_error,
            )
        )

    async def ready_receipt_ids(self, *, limit: int) -> list[UUID]:
        result = await self._session.execute(
            select(OFD_RECEIPTS_TABLE.c.id)
            .where(OFD_RECEIPTS_TABLE.c.status == OfdReceiptStatus.READY.value)
            .order_by(OFD_RECEIPTS_TABLE.c.doc_datetime)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def needs_location_receipts(
        self, reg_number: str, *, limit: int = 100
    ) -> list[OfdReceipt]:
        result = await self._session.execute(
            select(OFD_RECEIPTS_TABLE.c.id)
            .where(
                OFD_RECEIPTS_TABLE.c.reg_number == reg_number,
                OFD_RECEIPTS_TABLE.c.status
                == OfdReceiptStatus.NEEDS_LOCATION.value,
            )
            .order_by(OFD_RECEIPTS_TABLE.c.doc_datetime)
            .limit(limit)
        )

        receipts: list[OfdReceipt] = []
        for receipt_id in result.scalars().all():
            receipt = await self.get_by_id(receipt_id)
            if receipt is not None:
                receipts.append(receipt)

        return receipts

    async def add_sync_run(self, run: OfdSyncRun) -> None:
        await self._session.execute(
            insert(OFD_SYNC_RUNS_TABLE).values(
                id=run.id,
                inn=run.inn,
                reg_number=run.reg_number,
                period_from=run.period_from,
                period_to=run.period_to,
                started_at=run.started_at,
                finished_at=run.finished_at,
                status=run.status.value,
                receipts_found=run.receipts_found,
                receipts_created=run.receipts_created,
                error=run.error,
            )
        )

    async def save_sync_run(self, run: OfdSyncRun) -> None:
        await self._session.execute(
            update(OFD_SYNC_RUNS_TABLE)
            .where(OFD_SYNC_RUNS_TABLE.c.id == run.id)
            .values(
                finished_at=run.finished_at,
                status=run.status.value,
                receipts_found=run.receipts_found,
                receipts_created=run.receipts_created,
                error=run.error,
            )
        )

    async def alias_by_barcode(self, barcode: str) -> OfdProductAlias | None:
        normalized = normalize_barcode(barcode)
        if normalized is None:
            return None

        result = await self._session.execute(
            select(OFD_PRODUCT_ALIASES_TABLE).where(
                OFD_PRODUCT_ALIASES_TABLE.c.barcode == normalized
            )
        )
        row = result.mappings().one_or_none()
        if row is None:
            return None

        return self._to_alias(row)

    async def save_alias(self, alias: OfdProductAlias) -> None:
        await self._session.execute(
            pg_insert(OFD_PRODUCT_ALIASES_TABLE)
            .values(
                id=alias.id,
                barcode=alias.barcode,
                nomenclature_id=alias.nomenclature_id,
                created_by=alias.created_by,
                created_at=alias.created_at,
                updated_at=alias.updated_at,
            )
            .on_conflict_do_update(
                index_elements=[OFD_PRODUCT_ALIASES_TABLE.c.barcode],
                set_={
                    "nomenclature_id": alias.nomenclature_id,
                    "updated_at": func.now(),
                },
            )
        )

    @staticmethod
    def _line_values(line: OfdReceiptLine) -> dict:
        return {
            "id": line.id,
            "receipt_id": line.receipt_id,
            "line_number": line.line_number,
            "name": line.name,
            "barcode": line.barcode,
            "product_code": line.product_code,
            "quantity": line.quantity,
            "unit": line.unit,
            "price_kopecks": line.price_kopecks,
            "total_kopecks": line.total_kopecks,
            "nomenclature_id": line.nomenclature_id,
            "mapping_status": line.mapping_status.value,
            "mapping_error": line.mapping_error,
            "raw": line.raw,
            "created_at": line.created_at,
        }

    @staticmethod
    def _to_receipt(
        row: RowMapping, lines: list[OfdReceiptLine]
    ) -> OfdReceipt:
        return OfdReceipt(
            id=row["id"],
            inn=row["inn"],
            reg_number=row["reg_number"],
            fn_number=row["fn_number"],
            doc_number=row["doc_number"],
            fiscal_sign=row["fiscal_sign"],
            raw_id=row["raw_id"],
            doc_datetime=row["doc_datetime"],
            c_date_utc=row["c_date_utc"],
            operation_type=row["operation_type"],
            is_correction=row["is_correction"],
            is_bso=row["is_bso"],
            total_kopecks=row["total_kopecks"],
            cash_kopecks=row["cash_kopecks"],
            ecash_kopecks=row["ecash_kopecks"],
            org_unit_id=row["org_unit_id"],
            status=OfdReceiptStatus(row["status"]),
            error=row["error"],
            posted_at=row["posted_at"],
            posted_by=row["posted_by"],
            raw=row["raw"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            lines=lines,
        )

    @staticmethod
    def _to_line(row: RowMapping) -> OfdReceiptLine:
        return OfdReceiptLine(
            id=row["id"],
            receipt_id=row["receipt_id"],
            line_number=row["line_number"],
            name=row["name"],
            barcode=row["barcode"],
            product_code=row["product_code"],
            quantity=row["quantity"],
            unit=row["unit"],
            price_kopecks=row["price_kopecks"],
            total_kopecks=row["total_kopecks"],
            nomenclature_id=row["nomenclature_id"],
            mapping_status=OfdLineMappingStatus(row["mapping_status"]),
            mapping_error=row["mapping_error"],
            raw=row["raw"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _to_alias(row: RowMapping) -> OfdProductAlias:
        return OfdProductAlias(
            id=row["id"],
            barcode=row["barcode"],
            nomenclature_id=row["nomenclature_id"],
            created_by=row["created_by"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
