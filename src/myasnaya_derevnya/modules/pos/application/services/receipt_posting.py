import logging
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InsufficientStockError,
)
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
    SaleLine,
)
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceipt,
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)

logger = logging.getLogger(__name__)

QUANTITY_STEP = Decimal("0.000001")


class ReceiptPostingService:
    """Проводит чек DoKa по складу и фиксирует итоговый статус.

    Списывается именно проданная номенклатура: чек фиксирует факт продажи,
    а не производство. Разбор блюда на компоненты должен происходить в
    производственном задании, иначе магазин, продающий готовый товар,
    пытался бы списать сырьё, которого у него нет.
    """

    def __init__(
        self,
        receipt_repository: PosReceiptRepository,
        inventory_api: InventoryAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._receipt_repository = receipt_repository
        self._inventory_api = inventory_api
        self._transaction_manager = transaction_manager

    async def post(self, receipt: PosReceipt) -> PosReceipt:
        if receipt.status is PosReceiptStatus.POSTED:
            return receipt

        receipt.refresh_status()

        if receipt.status is PosReceiptStatus.IGNORED:
            await self._save(receipt)
            return receipt

        if receipt.status is PosReceiptStatus.NEEDS_MAPPING:
            await self._save(receipt)
            return receipt

        if await self._inventory_api.sale_posting_exists(receipt.id):
            receipt.mark_posted()
            await self._save(receipt)
            return receipt

        try:
            lines = await self._resolve_write_off(receipt)
            await self._inventory_api.post_sale(
                document_id=receipt.id,
                org_unit_id=receipt.org_unit_id,
                occurred_at=receipt.occurred_at,
                lines=lines,
                posted_by=None,
            )
        except InsufficientStockError as exc:
            await self._transaction_manager.rollback()
            return await self._finish_with_error(receipt, exc, needs_stock=True)
        except DocumentAlreadyPostedError:
            await self._transaction_manager.rollback()
            receipt.mark_posted()
            await self._save(receipt)
            return receipt
        except Exception as exc:  # noqa: BLE001 — чек не должен терять статус
            await self._transaction_manager.rollback()
            return await self._finish_with_error(receipt, exc, needs_stock=False)

        receipt.mark_posted()
        await self._save(receipt)

        logger.info(
            "Чек DoKa проведён по складу",
            extra={
                "receipt_id": str(receipt.id),
                "source_id": str(receipt.source_id),
                "org_unit_id": str(receipt.org_unit_id),
                "total_kopecks": receipt.total_kopecks,
            },
        )

        return receipt

    async def _finish_with_error(
        self,
        receipt: PosReceipt,
        exc: Exception,
        *,
        needs_stock: bool,
    ) -> PosReceipt:
        # Проведение могло успеть записаться, а ответ — потеряться.
        if await self._inventory_api.sale_posting_exists(receipt.id):
            receipt.mark_posted()
        elif needs_stock:
            receipt.mark_needs_stock(str(exc))
        else:
            receipt.mark_failed(str(exc))

        await self._save(receipt)

        logger.warning(
            "Не удалось провести чек DoKa",
            extra={
                "receipt_id": str(receipt.id),
                "source_id": str(receipt.source_id),
                "status": receipt.status.value,
                "error": str(exc),
            },
        )

        return receipt

    async def _save(self, receipt: PosReceipt) -> None:
        await self._receipt_repository.save(receipt)
        await self._transaction_manager.commit()

    async def _resolve_write_off(self, receipt: PosReceipt) -> list[SaleLine]:
        totals: dict[UUID, Decimal] = {}

        for line in receipt.lines:
            if line.nomenclature_id is None:
                continue

            _add(
                totals,
                line.nomenclature_id,
                line.quantity * line.unit_factor,
            )

        return [
            SaleLine(
                nomenclature_id=nomenclature_id,
                quantity=quantity.quantize(
                    QUANTITY_STEP, rounding=ROUND_HALF_UP
                ),
            )
            for nomenclature_id, quantity in totals.items()
            if quantity > 0
        ]


def _add(totals: dict[UUID, Decimal], nomenclature_id: UUID, quantity: Decimal) -> None:
    totals[nomenclature_id] = totals.get(nomenclature_id, Decimal(0)) + quantity
