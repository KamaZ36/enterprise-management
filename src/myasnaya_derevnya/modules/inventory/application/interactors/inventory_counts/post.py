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
from myasnaya_derevnya.modules.inventory.domain.entities.inventory_count import (
    InventoryCountLine,
)
from myasnaya_derevnya.modules.inventory.domain.entities.stock_movement import (
    MovementType,
)
from myasnaya_derevnya.modules.inventory.domain.errors import (
    DocumentAlreadyPostedError,
    InventoryCountNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.domain.value_objects.money import Money
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.inventory_count.base import (
    InventoryCountRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostInventoryCountCommand:
    inventory_count_id: UUID


class PostInventoryCountInteractor:
    """Проводит инвентаризацию: разницу учётного и фактического количества
    оформляет излишком (``inventory_surplus``) или недостачей
    (``inventory_shortage``). Излишек приходуется по текущей средней
    себестоимости, недостача списывается по FEFO или указанной партии.
    """

    def __init__(
        self,
        identity_provider: IdentityProvider,
        inventory_count_repository: InventoryCountRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._inventory_count_repository = inventory_count_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostInventoryCountCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        inventory_count = await self._inventory_count_repository.get_by_id(
            command.inventory_count_id
        )
        if inventory_count is None:
            raise InventoryCountNotFoundError(command.inventory_count_id)
        if not inventory_count.is_draft:
            raise DocumentAlreadyPostedError(inventory_count.id)

        lines = inventory_count.lines
        location = await self._preconditions.ensure_ready(
            org_unit_id=inventory_count.org_unit_id,
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
            document_type=DocumentType.INVENTORY_COUNT,
            document_id=inventory_count.id,
            org_unit_id=inventory_count.org_unit_id,
            occurred_at=inventory_count.occurred_at,
            posted_by=current_user_id,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (inventory_count.org_unit_id, line.nomenclature_id)
                    for line in lines
                ],
            )

            for line in lines:
                await self._apply_line(posting, inventory_count.org_unit_id, line)

        inventory_count.post()
        await self._inventory_count_repository.save(inventory_count)
        await self._transaction_manager.commit()

        logger.info(
            "Инвентаризация проведена",
            extra={
                "inventory_count_id": str(inventory_count.id),
                "org_unit_id": str(inventory_count.org_unit_id),
            },
        )

    async def _apply_line(
        self,
        posting: StockPostingHandle,
        org_unit_id: UUID,
        line: InventoryCountLine,
    ) -> None:
        book_quantity = await posting.balance_quantity(
            org_unit_id=org_unit_id,
            nomenclature_id=line.nomenclature_id,
        )
        delta = line.counted_quantity - book_quantity

        if delta == 0:
            return

        if delta > 0:
            await self._receive_surplus(posting, org_unit_id, line, delta)
        else:
            await self._issue_shortage(posting, org_unit_id, line, -delta)

    async def _receive_surplus(
        self,
        posting: StockPostingHandle,
        org_unit_id: UUID,
        line: InventoryCountLine,
        quantity: Decimal,
    ) -> None:
        lot_id = line.lot_id
        if lot_id is None and line.lot_code:
            lot_id = await self._lot_resolver.find_or_create(
                nomenclature_id=line.nomenclature_id,
                lot_code=line.lot_code,
            )

        if lot_id is not None:
            await posting.lock(
                lot_keys=[(org_unit_id, line.nomenclature_id, lot_id)]
            )

        unit_cost = await posting.balance_average_cost(
            org_unit_id=org_unit_id,
            nomenclature_id=line.nomenclature_id,
        )
        cost = Money.from_quantity_and_unit_cost(quantity, unit_cost)

        await posting.receive(
            org_unit_id=org_unit_id,
            nomenclature_id=line.nomenclature_id,
            quantity=quantity,
            cost=cost,
            movement_type=MovementType.INVENTORY_SURPLUS,
            lot_id=lot_id,
        )

    async def _issue_shortage(
        self,
        posting: StockPostingHandle,
        org_unit_id: UUID,
        line: InventoryCountLine,
        quantity: Decimal,
    ) -> None:
        slices = await self._shortage_slices(posting, org_unit_id, line, quantity)

        for lot_id, slice_quantity in slices:
            await posting.issue(
                org_unit_id=org_unit_id,
                nomenclature_id=line.nomenclature_id,
                quantity=slice_quantity,
                movement_type=MovementType.INVENTORY_SHORTAGE,
                lot_id=lot_id,
            )

    async def _shortage_slices(
        self,
        posting: StockPostingHandle,
        org_unit_id: UUID,
        line: InventoryCountLine,
        quantity: Decimal,
    ) -> list[tuple[UUID | None, Decimal]]:
        if line.lot_id is not None:
            await posting.lock(
                lot_keys=[(org_unit_id, line.nomenclature_id, line.lot_id)]
            )
            return [(line.lot_id, quantity)]

        if line.lot_code:
            lot_id = await self._lot_resolver.require(
                nomenclature_id=line.nomenclature_id,
                lot_code=line.lot_code,
            )
            await posting.lock(
                lot_keys=[(org_unit_id, line.nomenclature_id, lot_id)]
            )
            return [(lot_id, quantity)]

        return await posting.allocate(
            org_unit_id=org_unit_id,
            nomenclature_id=line.nomenclature_id,
            quantity=quantity,
        )
