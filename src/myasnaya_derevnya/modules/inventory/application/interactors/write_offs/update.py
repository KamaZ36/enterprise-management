import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.write_off import WriteOffLine
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    LocationNotFoundError,
    WriteOffNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateWriteOffLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateWriteOffCommand:
    write_off_id: UUID
    occurred_at: datetime
    lines: list[UpdateWriteOffLineCommand]
    reason: str | None = None
    comment: str | None = None


class UpdateWriteOffInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        write_off_repository: WriteOffRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._write_off_repository = write_off_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateWriteOffCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        write_off = await self._write_off_repository.get_by_id(command.write_off_id)
        if write_off is None:
            raise WriteOffNotFoundError(command.write_off_id)
        if not write_off.is_draft:
            raise DocumentAlreadyPostedError(write_off.id)

        location = await self._business_api.stock_location(write_off.org_unit_id)
        if location is None:
            raise LocationNotFoundError(write_off.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        write_off.revise(
            occurred_at=command.occurred_at,
            reason=command.reason,
            comment=command.comment,
            lines=[
                WriteOffLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    lot_code=line.lot_code,
                )
                for line in command.lines
            ],
        )

        await self._write_off_repository.save(write_off)
        await self._transaction_manager.commit()

        logger.info("Списание изменено", extra={"write_off_id": str(write_off.id)})
