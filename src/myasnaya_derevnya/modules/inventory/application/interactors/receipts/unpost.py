import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentNotPostedError,
    LocationNotFoundError,
    ReceiptNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.base import (
    ReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostReceiptCommand:
    receipt_id: UUID


class UnpostReceiptInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        receipt_repository: ReceiptRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._receipt_repository = receipt_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UnpostReceiptCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        receipt = await self._receipt_repository.get_by_id(command.receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(command.receipt_id)
        if receipt.status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(receipt.id)

        location = await self._business_api.stock_location(receipt.org_unit_id)
        if location is None:
            raise LocationNotFoundError(receipt.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._ledger.unpost(
            document_type=DocumentType.RECEIPT,
            document_id=receipt.id,
        )

        receipt.unpost()
        await self._receipt_repository.save(receipt)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение поступления отменено",
            extra={
                "receipt_id": str(receipt.id),
                "org_unit_id": str(receipt.org_unit_id),
            },
        )
