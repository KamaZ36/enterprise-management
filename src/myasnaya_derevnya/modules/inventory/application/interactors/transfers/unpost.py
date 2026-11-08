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
    TransferNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostTransferCommand:
    transfer_id: UUID


class UnpostTransferInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        transfer_repository: TransferRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._transfer_repository = transfer_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UnpostTransferCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        transfer = await self._transfer_repository.get_by_id(command.transfer_id)
        if transfer is None:
            raise TransferNotFoundError(command.transfer_id)
        if transfer.status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(transfer.id)

        location = await self._business_api.stock_location(
            transfer.from_org_unit_id
        )
        if location is None:
            raise LocationNotFoundError(transfer.from_org_unit_id)

        target = await self._business_api.stock_location(
            transfer.to_org_unit_id
        )
        if target is None:
            raise LocationNotFoundError(transfer.to_org_unit_id)

        for checked in (location, target):
            allowed = await self._staff_api.can(
                user_id=current_user_id,
                permission=POST_DOCUMENT,
                org_unit_id=checked.id,
            )
            if not allowed:
                raise ForbiddenError()

        await self._ledger.unpost(
            document_type=DocumentType.TRANSFER,
            document_id=transfer.id,
        )

        transfer.unpost()
        await self._transfer_repository.save(transfer)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение перемещения отменено",
            extra={
                "transfer_id": str(transfer.id),
                "from_org_unit_id": str(transfer.from_org_unit_id),
                "to_org_unit_id": str(transfer.to_org_unit_id),
            },
        )
