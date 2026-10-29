import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid7

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.pos.application.dto import (
    IncomingReceipt,
    PosImportReceiptResult,
    PosImportResult,
)
from myasnaya_derevnya.modules.pos.application.errors import (
    EmptyReceiptsBatchError,
    TooManyReceiptsError,
)
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from myasnaya_derevnya.modules.pos.application.status import agent_status
from myasnaya_derevnya.modules.pos.domain.entities.agent import PosAgent
from myasnaya_derevnya.modules.pos.domain.entities.import_batch import PosImportBatch
from myasnaya_derevnya.modules.pos.domain.entities.product_mapping import (
    PosProductMapping,
)
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceipt,
    PosReceiptLine,
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.domain.entities.source import PosSource
from myasnaya_derevnya.modules.pos.domain.errors import InvalidDokaGuidError
from myasnaya_derevnya.modules.pos.domain.value_objects.identifiers import (
    canonicalize_guid,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.agent.base import (
    PosAgentRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.import_batch.base import (
    PosImportBatchRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.base import (
    PosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)
from myasnaya_derevnya.utils import get_datetime_utc

logger = logging.getLogger(__name__)

MAX_RECEIPTS_PER_REQUEST = 100


@dataclass(frozen=True, slots=True)
class ImportPosReceiptsCommand:
    source: PosSource
    agent: PosAgent
    file_name: str
    file_sha256: str | None
    exported_at: datetime | None
    receipts: tuple[IncomingReceipt, ...]


class ImportPosReceiptsInteractor:
    """Принимает чеки от агента, сохраняет их и сразу проводит по складу."""

    def __init__(
        self,
        receipt_repository: PosReceiptRepository,
        import_batch_repository: PosImportBatchRepository,
        product_map_repository: PosProductMapRepository,
        agent_repository: PosAgentRepository,
        posting_service: ReceiptPostingService,
        transaction_manager: TransactionManager,
    ) -> None:
        self._receipt_repository = receipt_repository
        self._import_batch_repository = import_batch_repository
        self._product_map_repository = product_map_repository
        self._agent_repository = agent_repository
        self._posting_service = posting_service
        self._transaction_manager = transaction_manager

    async def __call__(self, command: ImportPosReceiptsCommand) -> PosImportResult:
        if not command.receipts:
            raise EmptyReceiptsBatchError()
        if len(command.receipts) > MAX_RECEIPTS_PER_REQUEST:
            raise TooManyReceiptsError()

        batch = PosImportBatch.start(
            source_id=command.source.id,
            agent_id=command.agent.id,
            file_name=command.file_name[:512],
            file_sha256=command.file_sha256,
            exported_at=command.exported_at,
            receipts_total=len(command.receipts),
        )
        await self._import_batch_repository.add(batch)
        await self._transaction_manager.commit()

        mappings = await self._load_mappings(
            source_id=command.source.id, receipts=command.receipts
        )

        results: list[PosImportReceiptResult] = []
        rejected = 0

        for incoming in command.receipts:
            try:
                result = await self._import_one(
                    source=command.source,
                    agent=command.agent,
                    batch=batch,
                    incoming=incoming,
                    mappings=mappings,
                )
            except Exception as exc:  # noqa: BLE001 — один чек не должен ломать пакет
                await self._transaction_manager.rollback()
                rejected += 1
                logger.warning(
                    "Чек DoKa отклонён при импорте",
                    extra={
                        "source_id": str(command.source.id),
                        "external_guid": incoming.guid,
                        "error": str(exc),
                    },
                )
                results.append(
                    PosImportReceiptResult(
                        guid=incoming.guid,
                        status="rejected",
                        message=str(exc)[:512],
                    )
                )
                batch.count_failed()
                continue

            results.append(result)

        batch.finish()
        await self._import_batch_repository.save(batch)

        if rejected and rejected == len(command.receipts):
            command.agent.mark_sync_error("Все чеки пакета отклонены")
        else:
            command.agent.mark_sync_success(last_success_at=get_datetime_utc())
        await self._agent_repository.save(command.agent)
        await self._transaction_manager.commit()

        logger.info(
            "Импорт продаж DoKa завершён",
            extra={
                "source_id": str(command.source.id),
                "agent_id": str(command.agent.id),
                "file_name": command.file_name,
                "receipts_total": batch.receipts_total,
                "receipts_created": batch.receipts_created,
                "receipts_duplicate": batch.receipts_duplicate,
                "receipts_posted": batch.receipts_posted,
                "receipts_pending": batch.receipts_pending,
                "receipts_failed": batch.receipts_failed,
                "receipts_rejected": rejected,
            },
        )

        return PosImportResult(
            server_time=get_datetime_utc(),
            batch_id=batch.id,
            results=tuple(results),
        )

    async def _import_one(
        self,
        *,
        source: PosSource,
        agent: PosAgent,
        batch: PosImportBatch,
        incoming: IncomingReceipt,
        mappings: dict[str, PosProductMapping],
    ) -> PosImportReceiptResult:
        guid = canonicalize_guid(incoming.guid)

        existing = await self._receipt_repository.get_by_source_guid(source.id, guid)
        if existing is not None:
            batch.count_duplicate()
            return await self._duplicate_result(existing)

        receipt = self._build_receipt(
            source=source,
            agent=agent,
            batch=batch,
            incoming=incoming,
            mappings=mappings,
        )

        added = await self._receipt_repository.add_if_absent(receipt)
        if not added:
            await self._transaction_manager.rollback()
            existing = await self._receipt_repository.get_by_source_guid(
                source.id, guid
            )
            batch.count_duplicate()
            if existing is None:
                return PosImportReceiptResult(
                    guid=guid,
                    status="duplicate",
                    message="Чек уже был принят ранее.",
                )
            return await self._duplicate_result(existing)

        await self._transaction_manager.commit()
        batch.count_created()

        receipt = await self._posting_service.post(receipt)
        self._count_by_status(batch, receipt)

        return PosImportReceiptResult(
            guid=guid,
            status=agent_status(receipt),
            message=receipt.error,
        )

    async def _duplicate_result(self, receipt: PosReceipt) -> PosImportReceiptResult:
        if not receipt.is_terminal:
            receipt = await self._posting_service.post(receipt)

        return PosImportReceiptResult(
            guid=receipt.external_guid,
            status="duplicate",
            message="Чек уже был принят ранее.",
        )

    def _build_receipt(
        self,
        *,
        source: PosSource,
        agent: PosAgent,
        batch: PosImportBatch,
        incoming: IncomingReceipt,
        mappings: dict[str, PosProductMapping],
    ) -> PosReceipt:
        receipt_id = uuid7()

        lines: list[PosReceiptLine] = []
        for index, item in enumerate(incoming.lines, start=1):
            product_guid = canonicalize_guid(item.product_guid)
            line = PosReceiptLine.create(
                receipt_id=receipt_id,
                line_number=index,
                external_guid=item.guid,
                product_guid=product_guid,
                product_name=item.product_name,
                unit=item.unit,
                quantity=item.quantity,
                price_kopecks=item.price_kopecks,
                amount_kopecks=item.amount_kopecks,
                discount_kopecks=item.discount_kopecks,
                barcode=item.barcode,
                mark_code=item.mark_code,
                raw=item.raw,
            )

            mapping = mappings.get(product_guid)
            if mapping is not None:
                line.map_to(
                    mapping.nomenclature_id, unit_factor=mapping.unit_factor
                )

            lines.append(line)

        return PosReceipt.create(
            receipt_id=receipt_id,
            source_id=source.id,
            agent_id=agent.id,
            batch_id=batch.id,
            external_guid=incoming.guid,
            occurred_at=incoming.occurred_at,
            kind=incoming.kind,
            payment_kind=incoming.payment_kind,
            total_kopecks=incoming.total_kopecks,
            subdivision_code=incoming.subdivision_code,
            subdivision_name=incoming.subdivision_name,
            cashier=incoming.cashier,
            shift=incoming.shift,
            number=incoming.number,
            fd_number=incoming.fd_number,
            fp_number=incoming.fp_number,
            fn_number=incoming.fn_number,
            org_unit_id=source.org_unit_id,
            lines=lines,
            raw=incoming.raw,
        )

    async def _load_mappings(
        self, *, source_id: UUID, receipts: tuple[IncomingReceipt, ...]
    ) -> dict[str, PosProductMapping]:
        guids: set[str] = set()

        for receipt in receipts:
            for line in receipt.lines:
                guid = _canonical_or_none(line.product_guid)
                if guid is not None:
                    guids.add(guid)

        return await self._product_map_repository.mappings_for(source_id, guids)

    @staticmethod
    def _count_by_status(batch: PosImportBatch, receipt: PosReceipt) -> None:
        if receipt.status is PosReceiptStatus.POSTED:
            batch.count_posted()
        elif receipt.status in (
            PosReceiptStatus.NEEDS_MAPPING,
            PosReceiptStatus.NEEDS_STOCK,
        ):
            batch.count_pending()
        else:
            batch.count_failed()


def _canonical_or_none(value: str) -> str | None:
    try:
        return canonicalize_guid(value)
    except InvalidDokaGuidError:
        return None
