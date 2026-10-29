from myasnaya_derevnya.modules.pos.application.dto import PosPostResult
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceipt,
    PosReceiptStatus,
)


def agent_status(receipt: PosReceipt) -> str:
    """Статус чека в терминах HTTP-контракта агента."""

    if receipt.status is PosReceiptStatus.POSTED:
        return "posted"
    if receipt.status is PosReceiptStatus.NEEDS_STOCK:
        return "pending_stock"
    if receipt.status is PosReceiptStatus.NEEDS_MAPPING:
        return "pending_unmapped"
    if receipt.status is PosReceiptStatus.IGNORED:
        return "rejected"

    return "rejected"


def post_result(receipt: PosReceipt) -> PosPostResult:
    return PosPostResult(
        receipt_id=receipt.id,
        status=agent_status(receipt),
        message=receipt.error,
    )
