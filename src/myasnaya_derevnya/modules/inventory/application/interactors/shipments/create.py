import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.services.document_numbering import (
    next_document_number,
)
from myasnaya_derevnya.modules.inventory.domain.entities.shipment import (
    Shipment,
    ShipmentLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.document_number.base import (
    DocumentNumberRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.shipment.base import (
    ShipmentRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ShipmentLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    lot_code: str | None = None


@dataclass(frozen=True, slots=True)
class CreateShipmentCommand:
    org_unit_id: UUID
    occurred_at: datetime
    recipient: str
    lines: list[ShipmentLineCommand]
    comment: str | None = None


class CreateShipmentInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        shipment_repository: ShipmentRepository,
        document_number_repository: DocumentNumberRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._shipment_repository = shipment_repository
        self._document_number_repository = document_number_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateShipmentCommand) -> UUID:
        current_user_id = await self._identity_provider.get_current_user_id()

        location = await self._business_api.stock_location(command.org_unit_id)
        if location is None:
            raise LocationNotFoundError(command.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        number = await next_document_number(
            self._document_number_repository,
            DocumentType.SHIPMENT,
            command.occurred_at,
        )

        shipment = Shipment.create(
            org_unit_id=command.org_unit_id,
            occurred_at=command.occurred_at,
            recipient=command.recipient,
            created_by=current_user_id,
            number=number,
            comment=command.comment,
            lines=[
                ShipmentLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    lot_code=line.lot_code,
                )
                for line in command.lines
            ],
        )

        await self._shipment_repository.add(shipment)
        await self._transaction_manager.commit()

        logger.info(
            "Создан черновик отгрузки",
            extra={
                "shipment_id": str(shipment.id),
                "org_unit_id": str(shipment.org_unit_id),
            },
        )

        return shipment.id
