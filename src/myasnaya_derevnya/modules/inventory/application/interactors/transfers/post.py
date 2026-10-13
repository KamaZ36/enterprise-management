from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.application.services.posting_preconditions import (
    PostingPreconditions,
)
from myasnaya_derevnya.modules.inventory.application.services.transfer_posting import (
    TransferPosting,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import Transfer
from myasnaya_derevnya.modules.inventory.domain.entities.warehouse import Warehouse
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    TransferNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


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

        warehouses = await self._ensure_warehouses_ready(transfer)
        await self._ensure_allowed(current_user_id, warehouses)

        await self._transfer_posting.post(transfer=transfer, posted_by=current_user_id)

        transfer.post()
        await self._transfer_repository.save(transfer)
        await self._transaction_manager.commit()

    async def _ensure_warehouses_ready(self, transfer: Transfer) -> list[Warehouse]:
        nomenclature_ids = [line.nomenclature_id for line in transfer.lines]

        return [
            await self._preconditions.ensure_ready(
                warehouse_id=warehouse_id,
                nomenclature_ids=nomenclature_ids,
            )
            for warehouse_id in (
                transfer.from_warehouse_id,
                transfer.to_warehouse_id,
            )
        ]

    async def _ensure_allowed(self, user_id: UUID, warehouses: list[Warehouse]) -> None:
        for warehouse in warehouses:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=POST_DOCUMENT,
                org_unit_id=warehouse.org_unit_id,
            )
            if not allowed:
                raise ForbiddenError()
