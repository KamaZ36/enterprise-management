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
    ShipmentNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_status import (
    DocumentStatus,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.shipment.base import (
    ShipmentRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UnpostShipmentCommand:
    shipment_id: UUID


class UnpostShipmentInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        shipment_repository: ShipmentRepository,
        business_api: BusinessAPI,
        staff_api: StaffAPI,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._shipment_repository = shipment_repository
        self._business_api = business_api
        self._staff_api = staff_api
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UnpostShipmentCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        shipment = await self._shipment_repository.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(command.shipment_id)
        if shipment.status is not DocumentStatus.POSTED:
            raise DocumentNotPostedError(shipment.id)

        location = await self._business_api.stock_location(shipment.org_unit_id)
        if location is None:
            raise LocationNotFoundError(shipment.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        await self._ledger.unpost(
            document_type=DocumentType.SHIPMENT,
            document_id=shipment.id,
        )

        shipment.unpost()
        await self._shipment_repository.save(shipment)
        await self._transaction_manager.commit()

        logger.info(
            "Проведение отгрузки отменено",
            extra={
                "shipment_id": str(shipment.id),
                "org_unit_id": str(shipment.org_unit_id),
            },
        )
