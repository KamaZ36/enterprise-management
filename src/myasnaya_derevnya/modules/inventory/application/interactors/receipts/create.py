import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.domain.entities.receipt import (
    Receipt,
    ReceiptLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.base import (
    ReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReceiptLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal = Decimal(0)
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class CreateReceiptCommand:
    org_unit_id: UUID
    occurred_at: datetime
    lines: list[ReceiptLineCommand]
    supplier_name: str | None = None
    supplier_document_number: str | None = None
    comment: str | None = None


class CreateReceiptInteractor:
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

    async def __call__(self, command: CreateReceiptCommand) -> UUID:
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

        receipt = Receipt.create(
            org_unit_id=command.org_unit_id,
            occurred_at=command.occurred_at,
            created_by=current_user_id,
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

        await self._receipt_repository.add(receipt)
        await self._transaction_manager.commit()

        logger.info(
            "Создан черновик поступления",
            extra={
                "receipt_id": str(receipt.id),
                "org_unit_id": str(receipt.org_unit_id),
            },
        )

        return receipt.id
