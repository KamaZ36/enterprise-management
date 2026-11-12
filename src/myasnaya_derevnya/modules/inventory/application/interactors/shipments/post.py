import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.inventory.application.services.lot_resolver import (
    LotResolver,
)
from myasnaya_derevnya.modules.inventory.application.services.posting_preconditions import (
    PostingPreconditions,
)
from myasnaya_derevnya.modules.inventory.application.services.stock_ledger import (
    StockLedger,
    StockPostingHandle,
)
from myasnaya_derevnya.modules.inventory.domain.entities.shipment import ShipmentLine
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    ShipmentNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.shipment.base import (
    ShipmentRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostShipmentCommand:
    shipment_id: UUID


class PostShipmentInteractor:
    """Списывает товар со склада и фиксирует себестоимость отгрузки."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        shipment_repository: ShipmentRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._shipment_repository = shipment_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostShipmentCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        shipment = await self._shipment_repository.get_by_id(command.shipment_id)
        if shipment is None:
            raise ShipmentNotFoundError(command.shipment_id)
        if not shipment.is_draft:
            raise DocumentAlreadyPostedError(shipment.id)

        lines = shipment.lines
        location = await self._preconditions.ensure_ready(
            org_unit_id=shipment.org_unit_id,
            nomenclature_ids=[line.nomenclature_id for line in lines],
        )

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        async with self._ledger.posting(
            document_type=DocumentType.SHIPMENT,
            document_id=shipment.id,
            org_unit_id=shipment.org_unit_id,
            occurred_at=shipment.occurred_at,
            posted_by=current_user_id,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (shipment.org_unit_id, line.nomenclature_id) for line in lines
                ],
            )

            for line in lines:
                slices = await self._line_slices(
                    posting, shipment.org_unit_id, line
                )
                for lot_id, quantity in slices:
                    await posting.issue(
                        org_unit_id=shipment.org_unit_id,
                        nomenclature_id=line.nomenclature_id,
                        quantity=quantity,
                        movement_type=MovementType.SHIPMENT,
                        lot_id=lot_id,
                    )

        shipment.post()
        await self._shipment_repository.save(shipment)
        await self._transaction_manager.commit()

        logger.info(
            "Отгрузка проведена",
            extra={
                "shipment_id": str(shipment.id),
                "org_unit_id": str(shipment.org_unit_id),
                "recipient": shipment.recipient,
            },
        )

    async def _line_slices(
        self,
        posting: StockPostingHandle,
        org_unit_id: UUID,
        line: ShipmentLine,
    ) -> list[tuple[UUID | None, Decimal]]:
        if line.lot_id is not None:
            await posting.lock(
                lot_keys=[(org_unit_id, line.nomenclature_id, line.lot_id)]
            )
            return [(line.lot_id, line.quantity)]

        if line.lot_code:
            lot_id = await self._lot_resolver.require(
                nomenclature_id=line.nomenclature_id,
                lot_code=line.lot_code,
            )
            await posting.lock(lot_keys=[(org_unit_id, line.nomenclature_id, lot_id)])
            return [(lot_id, line.quantity)]

        return await posting.allocate(
            org_unit_id=org_unit_id,
            nomenclature_id=line.nomenclature_id,
            quantity=line.quantity,
        )
