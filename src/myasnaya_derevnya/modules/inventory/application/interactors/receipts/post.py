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
from myasnaya_derevnya.modules.veterinary.presentation.veterinary_api import (
    VeterinaryAPI,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostReceiptCommand:
    receipt_id: UUID


class PostReceiptInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        receipt_repository: ReceiptRepository,
        staff_api: StaffAPI,
        preconditions: PostingPreconditions,
        lot_resolver: LotResolver,
        ledger: StockLedger,
        veterinary_api: VeterinaryAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._receipt_repository = receipt_repository
        self._staff_api = staff_api
        self._preconditions = preconditions
        self._lot_resolver = lot_resolver
        self._ledger = ledger
        self._veterinary_api = veterinary_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostReceiptCommand) -> None:
        current_user_id = await self._identity_provider.get_current_user_id()

        receipt = await self._receipt_repository.get_by_id(command.receipt_id)
        if receipt is None:
            raise ReceiptNotFoundError(command.receipt_id)
        if not receipt.is_draft:
            raise DocumentAlreadyPostedError(receipt.id)

        lines = receipt.lines
        location = await self._preconditions.ensure_ready(
            org_unit_id=receipt.org_unit_id,
            nomenclature_ids=[line.nomenclature_id for line in lines],
        )

        allowed = await self._staff_api.can(
            user_id=current_user_id,
            permission=POST_DOCUMENT,
            org_unit_id=location.id,
        )
        if not allowed:
            raise ForbiddenError()

        lot_ids = await self._resolve_lots(receipt, current_user_id)

        async with self._ledger.posting(
            document_type=DocumentType.RECEIPT,
            document_id=receipt.id,
            org_unit_id=receipt.org_unit_id,
            occurred_at=receipt.occurred_at,
            posted_by=current_user_id,
        ) as posting:
            await posting.lock(
                balance_keys=[
                    (receipt.org_unit_id, line.nomenclature_id) for line in lines
                ],
                lot_keys=[
                    (receipt.org_unit_id, line.nomenclature_id, lot_id)
                    for line, lot_id in zip(lines, lot_ids, strict=True)
                    if lot_id is not None
                ],
            )

            for line, lot_id in zip(lines, lot_ids, strict=True):
                await posting.receive(
                    org_unit_id=receipt.org_unit_id,
                    nomenclature_id=line.nomenclature_id,
                    quantity=line.quantity,
                    cost=line.total_cost,
                    movement_type=MovementType.RECEIPT,
                    lot_id=lot_id,
                )

        receipt.post()
        await self._receipt_repository.save(receipt)
        await self._receipt_repository.attach_lot_ids(
            receipt.id,
            {
                line.id: lot_id
                for line, lot_id in zip(receipt.lines, lot_ids, strict=True)
                if line.lot_id is None and lot_id is not None
            },
        )
        await self._transaction_manager.commit()

        logger.info(
            "Поступление проведено",
            extra={
                "receipt_id": str(receipt.id),
                "org_unit_id": str(receipt.org_unit_id),
            },
        )

    async def _resolve_lots(
        self, receipt, current_user_id: UUID
    ) -> list[UUID | None]:
        lot_ids: list[UUID | None] = []

        for line in receipt.lines:
            existing = None
            if line.lot_id is not None:
                existing = await self._lot_resolver.get(line.lot_id)
                await self._lot_resolver.ensure_matches(
                    nomenclature_id=line.nomenclature_id,
                    lot_id=line.lot_id,
                )
            else:
                existing = await self._lot_resolver.get_existing(
                    nomenclature_id=line.nomenclature_id,
                    lot_code=line.lot_code,
                    produced_at=None,
                    supplier_name=receipt.supplier_name,
                )

            document_id = (
                existing.veterinary_document_id
                if existing is not None
                else None
            )
            if _line_has_vetis(line) and document_id is None:
                document_id = await self._veterinary_api.create_manual_document(
                    org_unit_id=receipt.org_unit_id,
                    number=line.vetis_vsd_number,
                    guid=line.vetis_vsd_guid,
                    batch_id=line.vetis_batch_id,
                    product_item_guid=line.vetis_product_item_guid,
                    created_by=current_user_id,
                )

            if existing is not None:
                if _line_has_vetis(line) and document_id is not None:
                    await self._lot_resolver.attach_vetis(
                        nomenclature_id=line.nomenclature_id,
                        lot_id=existing.id,
                        vetis_vsd_number=line.vetis_vsd_number,
                        vetis_vsd_guid=line.vetis_vsd_guid,
                        vetis_batch_id=line.vetis_batch_id,
                        vetis_product_item_guid=line.vetis_product_item_guid,
                        vetis_entered_by=current_user_id,
                        veterinary_document_id=document_id,
                    )
                lot_ids.append(existing.id)
                continue

            lot_ids.append(
                await self._lot_resolver.find_or_create(
                    nomenclature_id=line.nomenclature_id,
                    lot_code=line.lot_code,
                    expires_at=line.expires_at,
                    supplier_name=receipt.supplier_name,
                    origin_org_unit_id=receipt.org_unit_id,
                    vetis_vsd_number=line.vetis_vsd_number,
                    vetis_vsd_guid=line.vetis_vsd_guid,
                    vetis_batch_id=line.vetis_batch_id,
                    vetis_product_item_guid=line.vetis_product_item_guid,
                    vetis_entered_by=current_user_id,
                    veterinary_document_id=document_id,
                )
            )

        return lot_ids


def _line_has_vetis(line) -> bool:
    return any(
        value is not None
        for value in (
            line.vetis_vsd_number,
            line.vetis_vsd_guid,
            line.vetis_batch_id,
            line.vetis_product_item_guid,
        )
    )
