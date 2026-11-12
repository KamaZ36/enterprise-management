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
    ShipmentNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.shipment.base import (
    ShipmentRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeleteShipmentCommand:
    shipment_id: UUID


class DeleteShipmentInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        shipment_repository: ShipmentRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._shipment_repository = shipment_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: DeleteShipmentCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        shipment = await self._shipment_repository.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(command.shipment_id)
        if not shipment.is_draft:
            raise DocumentAlreadyPostedError(shipment.id)

        location = await self._business_api.stock_location(shipment.org_unit_id)
        if location is None:
            raise LocationNotFoundError(shipment.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._shipment_repository.delete(shipment.id)
        await self._transaction_manager.commit()

        logger.info(
            "Черновик отгрузки удалён",
            extra={"shipment_id": str(shipment.id)},
        )
