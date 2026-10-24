import logging
from dataclasses import dataclass
from datetime import datetime

from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.fiscal.application.dto import OfdSyncResult
from myasnaya_derevnya.modules.fiscal.application.services.ofd_sync import (
    OfdSyncService,
)
from myasnaya_derevnya.modules.fiscal.domain.permissions import (
    CASH_REGISTER_RECEIPT_SYNC,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SyncOfdReceiptsCommand:
    reg_number: str
    date_from: datetime
    date_to: datetime


class SyncOfdReceiptsInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        sync_service: OfdSyncService,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._sync_service = sync_service

    async def __call__(self, command: SyncOfdReceiptsCommand) -> OfdSyncResult:
        user_id = await self._identity_provider.get_current_user_id()

        if not await self._staff_api.can_anywhere(
            user_id=user_id, permission=CASH_REGISTER_RECEIPT_SYNC
        ):
            raise ForbiddenError()

        return await self._sync_service.sync(
            reg_number=command.reg_number,
            date_from=command.date_from,
            date_to=command.date_to,
        )
