import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
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
class DeleteWriteOffCommand:
    write_off_id: UUID


class DeleteWriteOffInteractor:
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

    async def __call__(self, command: DeleteWriteOffCommand) -> None:
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

        await self._write_off_repository.delete(write_off.id)
        await self._transaction_manager.commit()

        logger.info(
            "Черновик списания удалён",
            extra={"write_off_id": str(write_off.id)},
        )
