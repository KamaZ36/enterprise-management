import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import StockLocation
from myasnaya_derevnya.modules.inventory.application.services.posting_preconditions import (
    PostingPreconditions,
)
from myasnaya_derevnya.modules.inventory.application.services.transfer_posting import (
    TransferPosting,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import Transfer
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    TransferNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostTransferCommand:
    transfer_id: UUID


class PostTransferInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        transfer_repository: TransferRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        transfer_posting: TransferPosting,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._transfer_repository = transfer_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._transfer_posting = transfer_posting
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostTransferCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        transfer = await self._transfer_repository.get_by_id(command.transfer_id)
        if transfer is None:
            raise TransferNotFoundError(command.transfer_id)
        if not transfer.is_draft:
            raise DocumentAlreadyPostedError(transfer.id)

        locations = await self._ensure_locations_ready(transfer)
        await self._ensure_allowed(current_user_id, locations)

        await self._transfer_posting.post(transfer=transfer, posted_by=current_user_id)

        transfer.post()
        await self._transfer_repository.save(transfer)
        await self._transaction_manager.commit()

        logger.info(
            "Перемещение проведено",
            extra={
                "transfer_id": str(transfer.id),
                "from_org_unit_id": str(transfer.from_org_unit_id),
                "to_org_unit_id": str(transfer.to_org_unit_id),
            },
        )

    async def _ensure_locations_ready(
        self, transfer: Transfer
    ) -> list[StockLocation]:
        nomenclature_ids = [line.nomenclature_id for line in transfer.lines]

        return [
            await self._preconditions.ensure_ready(
                org_unit_id=org_unit_id,
                nomenclature_ids=nomenclature_ids,
            )
            for org_unit_id in (
                transfer.from_org_unit_id,
                transfer.to_org_unit_id,
            )
        ]

    async def _ensure_allowed(
        self, user_id: UUID, locations: list[StockLocation]
    ) -> None:
        for location in locations:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=POST_DOCUMENT,
                org_unit_id=location.id,
            )
            if not allowed:
                raise ForbiddenError()
