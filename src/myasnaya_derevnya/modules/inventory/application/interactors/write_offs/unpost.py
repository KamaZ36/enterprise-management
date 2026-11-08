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
    WriteOffNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.write_off.base import (
    WriteOffRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostWriteOffCommand:
    write_off_id: UUID


class UnpostWriteOffInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        write_off_repository: WriteOffRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._write_off_repository = write_off_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UnpostWriteOffCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        write_off = await self._write_off_repository.get_by_id(command.write_off_id)
        if write_off is None:
            raise WriteOffNotFoundError(command.write_off_id)
        if write_off.status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(write_off.id)

        location = await self._business_api.stock_location(write_off.org_unit_id)
        if location is None:
            raise LocationNotFoundError(write_off.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._ledger.unpost(
            document_type=DocumentType.WRITE_OFF,
            document_id=write_off.id,
        )

        write_off.unpost()
        await self._write_off_repository.save(write_off)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение списания отменено",
            extra={
                "write_off_id": str(write_off.id),
                "org_unit_id": str(write_off.org_unit_id),
            },
        )
