from dataclasses import dataclass

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.pos.application.dto import (
    PosBatchPostResult,
    PosPostResult,
)
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from myasnaya_derevnya.modules.pos.application.status import post_result
from myasnaya_derevnya.modules.pos.domain.entities.receipt import (
    PosReceiptStatus,
)
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_MANAGE
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

PENDING_STATUSES = (
    PosReceiptStatus.NEW.value,
    PosReceiptStatus.NEEDS_MAPPING.value,
    PosReceiptStatus.READY.value,
    PosReceiptStatus.NEEDS_STOCK.value,
    PosReceiptStatus.FAILED.value,
)


@dataclass(frozen=True, slots=True)
class PostPendingPosReceiptsCommand:
    limit: int = 100


class PostPendingPosReceiptsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        receipt_repository: PosReceiptRepository,
        posting_service: ReceiptPostingService,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._receipt_repository = receipt_repository
        self._posting_service = posting_service

    async def __call__(
        self, command: PostPendingPosReceiptsCommand
    ) -> PosBatchPostResult:
        user_id = await self._identity_provider.get_current_user_id()
        scope = await self._staff_api.scope_for(
            user_id=user_id, permission=POS_RECEIPT_MANAGE
        )
        if scope.is_empty():
            raise ForbiddenError()

        receipt_ids = await self._receipt_repository.pending_receipt_ids(
            statuses=PENDING_STATUSES, limit=command.limit
        )

        results: list[PosPostResult] = []
        for receipt_id in receipt_ids:
            receipt = await self._receipt_repository.get_by_id(receipt_id)
            if receipt is None or not scope.covers(receipt.org_unit_id):
                continue

            receipt = await self._posting_service.post(receipt)
            results.append(post_result(receipt))

        posted = sum(1 for result in results if result.status == "posted")
        pending = sum(
            1
            for result in results
            if result.status in ("pending_unmapped", "pending_stock")
        )
        failed = len(results) - posted - pending

        return PosBatchPostResult(
            posted=posted,
            pending=pending,
            failed=failed,
            results=tuple(results),
        )
