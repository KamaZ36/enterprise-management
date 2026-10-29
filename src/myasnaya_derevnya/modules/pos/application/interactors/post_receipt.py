from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.pos.application.dto import PosPostResult
from myasnaya_derevnya.modules.pos.application.errors import PosReceiptNotFoundError
from myasnaya_derevnya.modules.pos.application.services.receipt_posting import (
    ReceiptPostingService,
)
from myasnaya_derevnya.modules.pos.application.status import post_result
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_MANAGE
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class PostPosReceiptCommand:
    receipt_id: UUID


class PostPosReceiptInteractor:
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

    async def __call__(self, command: PostPosReceiptCommand) -> PosPostResult:
        user_id = await self._identity_provider.get_current_user_id()

        receipt = await self._receipt_repository.get_by_id(command.receipt_id)
        if receipt is None:
            raise PosReceiptNotFoundError(command.receipt_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_RECEIPT_MANAGE,
            org_unit_id=receipt.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        receipt = await self._posting_service.post(receipt)

        return post_result(receipt)
