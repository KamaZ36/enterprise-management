import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.catalog.application.errors import (
    NomenclatureNotFound,
    StopListLocationNotFound,
)
from myasnaya_derevnya.modules.catalog.domain.entities.stop_list_entry import (
    StopListEntry,
)
from myasnaya_derevnya.modules.catalog.domain.permissions import MANAGE_STOP_LIST
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.nomenclature.base import (
    NomenclatureRepository,
)
from myasnaya_derevnya.modules.catalog.infrastructure.repositories.stop_list.base import (
    StopListEntryRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AddStopListItemCommand:
    org_unit_id: UUID
    nomenclature_id: UUID


class AddStopListItemInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        nomenclature_repository: NomenclatureRepository,
        stop_list_repository: StopListEntryRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._staff_api = staff_api
        self._nomenclature_repository = nomenclature_repository
        self._stop_list_repository = stop_list_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: AddStopListItemCommand) -> None:
        user_id = await self._identity_provider.get_current_user_id()

        location = await self._business_api.stock_location(command.org_unit_id)
        if location is None:
            raise StopListLocationNotFound(command.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=MANAGE_STOP_LIST,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        nomenclature = await self._nomenclature_repository.get_by_id(
            command.nomenclature_id
        )
        if nomenclature is None:
            raise NomenclatureNotFound(command.nomenclature_id)

        added = await self._stop_list_repository.add(
            StopListEntry.create(
                org_unit_id=command.org_unit_id,
                nomenclature_id=command.nomenclature_id,
                created_by=user_id,
            )
        )
        await self._transaction_manager.commit()

        if added:
            logger.info(
                "Товар добавлен в стоп-лист",
                extra={
                    "org_unit_id": str(command.org_unit_id),
                    "nomenclature_id": str(command.nomenclature_id),
                },
            )
