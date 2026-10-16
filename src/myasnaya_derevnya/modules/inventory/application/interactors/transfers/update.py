from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    LocationNotFoundError,
    TransferNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class UpdateTransferLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateTransferCommand:
    transfer_id: UUID
    occurred_at: datetime
    lines: list[UpdateTransferLineCommand]
    comment: str | None = None


class UpdateTransferInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        transfer_repository: TransferRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._transfer_repository = transfer_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateTransferCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        transfer = await self._transfer_repository.get_by_id(command.transfer_id)
        if transfer is None:
            raise TransferNotFoundError(command.transfer_id)
        if not transfer.is_draft:
            raise DocumentAlreadyPostedError(transfer.id)

        for org_unit_id in (transfer.from_org_unit_id, transfer.to_org_unit_id):
            location = await self._business_api.stock_location(org_unit_id)
            if location is None:
                raise LocationNotFoundError(org_unit_id)

            allowed = await self._staff_api.can(
                user_id=current_user_id,
                permission=CREATE_DOCUMENT,
                org_unit_id=location.id,
            )
            if not allowed:
                raise ForbiddenError()

        transfer.revise(
            occurred_at=command.occurred_at,
            comment=command.comment,
            lines=[
                TransferLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    lot_code=line.lot_code,
                )
                for line in command.lines
            ],
        )

        await self._transfer_repository.save(transfer)
        await self._transaction_manager.commit()
