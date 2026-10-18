import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import (
    BusinessAPI,
    StockLocation,
)
from myasnaya_derevnya.modules.inventory.domain.entities.transfer import (
    Transfer,
    TransferLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.transfer.base import (
    TransferRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TransferLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None = None


@dataclass(frozen=True, slots=True)
class CreateTransferCommand:
    from_org_unit_id: UUID
    to_org_unit_id: UUID
    occurred_at: datetime
    lines: list[TransferLineCommand]
    comment: str | None = None


class CreateTransferInteractor:
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

    async def __call__(self, command: CreateTransferCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()

        from_location = await self._business_api.stock_location(
            command.from_org_unit_id
        )
        if from_location is None:
            raise LocationNotFoundError(command.from_org_unit_id)

        to_location = await self._business_api.stock_location(command.to_org_unit_id)
        if to_location is None:
            raise LocationNotFoundError(command.to_org_unit_id)

        await self._ensure_allowed(current_user_id, (from_location, to_location))

        transfer = Transfer.create(
            from_org_unit_id=command.from_org_unit_id,
            to_org_unit_id=command.to_org_unit_id,
            occurred_at=command.occurred_at,
            created_by=current_user_id,
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

        await self._transfer_repository.add(transfer)
        await self._transaction_manager.commit()

        logger.info(
            "Создан черновик перемещения",
            extra={
                "transfer_id": str(transfer.id),
                "from_org_unit_id": str(transfer.from_org_unit_id),
                "to_org_unit_id": str(transfer.to_org_unit_id),
            },
        )

        return transfer.id

    async def _ensure_allowed(
        self, user_id: UUID, locations: tuple[StockLocation, ...]
    ) -> None:
        for location in locations:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=CREATE_DOCUMENT,
                org_unit_id=location.id,
            )
            if not allowed:
                raise ForbiddenError()
