import logging
from dataclasses import dataclass
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
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    OpeningBalanceNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import (
    MANAGE_OPENING_BALANCE,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.opening_balance.base import (
    OpeningBalanceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostOpeningBalanceCommand:
    opening_balance_id: UUID


class PostOpeningBalanceInteractor:
    """Оприходует начальные остатки по указанной себестоимости и партиям."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        opening_balance_repository: OpeningBalanceRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._opening_balance_repository = opening_balance_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostOpeningBalanceCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        opening_balance = await self._opening_balance_repository.get_by_id(
            command.opening_balance_id
        )
        if opening_balance is None:
            raise OpeningBalanceNotFoundError(command.opening_balance_id)
        if not opening_balance.is_draft:
            raise DocumentAlreadyPostedError(opening_balance.id)

        lines = opening_balance.lines
        location = await self._preconditions.ensure_ready(
            org_unit_id=opening_balance.org_unit_id,
            nomenclature_ids=[line.nomenclature_id for line in lines],
        )

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=MANAGE_OPENING_BALANCE,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        lot_ids = await self._resolve_lots(opening_balance, current_user_id)

        async with self._ledger.posting(
            document_type=DocumentType.OPENING_BALANCE,
            document_id=opening_balance.id,
            org_unit_id=opening_balance.org_unit_id,
            occurred_at=opening_balance.occurred_at,
            posted_by=current_user_id,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (opening_balance.org_unit_id, line.nomenclature_id)
                    for line in lines
                ],
                lot_keys=[
                    (opening_balance.org_unit_id, line.nomenclature_id, lot_id)
                    for line, lot_id in zip(lines, lot_ids, strict=True)
                    if lot_id is not None
                ],
            )

            for line, lot_id in zip(lines, lot_ids, strict=True):
                await posting.receive(
                    org_unit_id=opening_balance.org_unit_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    cost=line.total_cost,
                    movement_type=MovementType.OPENING_BALANCE,
                    lot_id=lot_id,
                )

        opening_balance.post()
        await self._opening_balance_repository.save(opening_balance)
        await self._opening_balance_repository.attach_lot_ids(
            opening_balance.id,
            {
                line.id: lot_id
                for line, lot_id in zip(opening_balance.lines, lot_ids, strict=True)
                if line.lot_id is None and lot_id is not None
            },
        )
        await self._transaction_manager.commit()

        logger.info(
            "Ввод начальных остатков проведён",
            extra={
                "opening_balance_id": str(opening_balance.id),
                "org_unit_id": str(opening_balance.org_unit_id),
            },
        )

    async def _resolve_lots(
        self, opening_balance, current_user_id: UUID
    ) -> list[UUID | None]:
        lot_ids: list[UUID | None] = []

        for line in opening_balance.lines:
            if line.lot_id is not None:
                await self._lot_resolver.ensure_matches(
                    nomenclature_id=line.nomenclature_id,
                    lot_id=line.lot_id,
                )
                lot_ids.append(line.lot_id)
                continue

            lot_ids.append(
                await self._lot_resolver.find_or_create(
                    nomenclature_id=line.nomenclature_id,
                    lot_code=line.lot_code,
                    expires_at=line.expires_at,
                    origin_org_unit_id=opening_balance.org_unit_id,
                )
            )

        return lot_ids
