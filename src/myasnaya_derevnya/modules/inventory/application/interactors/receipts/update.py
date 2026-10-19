import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.receipt import ReceiptLine
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    LocationNotFoundError,
    ReceiptNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.base import (
    ReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpdateReceiptLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal = Decimal(0)
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class UpdateReceiptCommand:
    receipt_id: UUID
    occurred_at: datetime
    lines: list[UpdateReceiptLineCommand]
    supplier_name: str | None = None
    supplier_document_number: str | None = None
    comment: str | None = None


class UpdateReceiptInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        receipt_repository: ReceiptRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._receipt_repository = receipt_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: UpdateReceiptCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        receipt = await self._receipt_repository.get_by_id(command.receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(command.receipt_id)
        if not receipt.is_draft:
            raise DocumentAlreadyPostedError(receipt.id)

        location = await self._business_api.stock_location(receipt.org_unit_id)
        if location is None:
            raise LocationNotFoundError(receipt.org_unit_id)

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=CREATE_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        receipt.revise(
            occurred_at=command.occurred_at,
            supplier_name=command.supplier_name,
            supplier_document_number=command.supplier_document_number,
            comment=command.comment,
            lines=[
                ReceiptLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    unit_cost=line.unit_cost,
                    lot_code=line.lot_code,
                    expires_at=line.expires_at,
                )
                for line in command.lines
            ],
        )

        await self._receipt_repository.save(receipt)
        await self._transaction_manager.commit()

        logger.info("Поступление изменено", extra={"receipt_id": str(receipt.id)})
