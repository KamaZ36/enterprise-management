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
    ReceiptNotFoundError,
)
from myasnaya_derevnya.modules.inventory.domain.permissions import POST_DOCUMENT
from myasnaya_derevnya.modules.inventory.domain.value_objects.document_type import (
    DocumentType,
)
from myasnaya_derevnya.modules.inventory.infrastructure.repositories.receipt.base import (
    ReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI


@dataclass(frozen=True, slots=True)
class PostReceiptCommand:
    receipt_id: UUID


class PostReceiptInteractor:
    """Проведение поступления: стоимость берётся из строк документа."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        receipt_repository: ReceiptRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._receipt_repository = receipt_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostReceiptCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        receipt = await self._receipt_repository.get_by_id(command.receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(command.receipt_id)
        if not receipt.is_draft:
            raise DocumentAlreadyPostedError(receipt.id)

        lines = receipt.lines
        warehouse = await self._preconditions.ensure_ready(
            warehouse_id=receipt.warehouse_id,
            nomenclature_ids=[line.nomenclature_id for line in lines],
        )

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=warehouse.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        lot_ids = await self._resolve_lots(receipt)

        async with self._ledger.posting(
            document_type=DocumentType.RECEIPT,
            document_id=receipt.id,
            warehouse_id=receipt.warehouse_id,
            occurred_at=receipt.occurred_at,
            posted_by=current_user_id,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (receipt.warehouse_id, line.nomenclature_id) for line in lines
                ],
                lot_keys=[
                    (receipt.warehouse_id, line.nomenclature_id, lot_id)
                    for line, lot_id in zip(lines, lot_ids, strict=True)
                    if lot_id is not None
                ],
            )

            for line, lot_id in zip(lines, lot_ids, strict=True):
                await posting.receive(
                    warehouse_id=receipt.warehouse_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    cost=line.total_cost,
                    movement_type=MovementType.RECEIPT,
                    lot_id=lot_id,
                )

        receipt.post()
        await self._receipt_repository.save(receipt)
        await self._transaction_manager.commit()

    async def _resolve_lots(self, receipt) -> list[UUID | None]:
        """Поступление может завести партию, если её ещё нет."""
        lot_ids: list[UUID | None] = []

        for line in receipt.lines:
            if line.lot_id is not None:
                lot_ids.append(line.lot_id)
                continue

            lot_ids.append(
                await self._lot_resolver.find_or_create(
                    nomenclature_id=line.nomenclature_id,
                    lot_code=line.lot_code,
                    expires_at=line.expires_at,
                    supplier_name=receipt.supplier_name,
                )
            )

        return lot_ids
