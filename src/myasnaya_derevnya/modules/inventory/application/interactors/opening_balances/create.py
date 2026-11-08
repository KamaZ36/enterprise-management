import logging
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.business.presentation.business_api import BusinessAPI
from myasnaya_derevnya.modules.inventory.application.services.document_numbering import (
    next_document_number,
)
from myasnaya_derevnya.modules.inventory.domain.entities.opening_balance import (
    OpeningBalance,
    OpeningBalanceLine,
)
from myasnaya_derevnya.modules.inventory.domain.errors import LocationNotFoundError
from myasnaya_derevnya.modules.inventory.domain.permissions import CREATE_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.document_number.base import (
    DocumentNumberRepository,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.opening_balance.base import (
    OpeningBalanceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OpeningBalanceLineCommand:
    nomenclature_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    lot_code: str | None = None
    expires_at: date | None = None


@dataclass(frozen=True, slots=True)
class CreateOpeningBalanceCommand:
    org_unit_id: UUID
    occurred_at: datetime
    lines: list[OpeningBalanceLineCommand]
    comment: str | None = None


class CreateOpeningBalanceInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        business_api: BusinessAPI,
        opening_balance_repository: OpeningBalanceRepository,
        document_number_repository: DocumentNumberRepository,
        staff_api: StaffAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._business_api = business_api
        self._opening_balance_repository = opening_balance_repository
        self._document_number_repository = document_number_repository
        self._staff_api = staff_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: CreateOpeningBalanceCommand) -> UUID:
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
            DocumentType.OPENING_BALANCE,
            command.occurred_at,
        )

        opening_balance = OpeningBalance.create(
            org_unit_id=command.org_unit_id,
            occurred_at=command.occurred_at,
            created_by=current_user_id,
            number=number,
            comment=command.comment,
            lines=[
                OpeningBalanceLine.create(
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    unit_cost=line.unit_cost,
                    lot_code=line.lot_code,
                    expires_at=line.expires_at,
                )
                for line in command.lines
            ],
        )

        await self._opening_balance_repository.add(opening_balance)
        await self._transaction_manager.commit()

        logger.info(
            "Создан черновик ввода начальных остатков",
            extra={
                "opening_balance_id": str(opening_balance.id),
                "org_unit_id": str(opening_balance.org_unit_id),
            },
        )

        return opening_balance.id
