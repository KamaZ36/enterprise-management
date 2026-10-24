import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.fiscal.application.dto import OfdPostResult
from myasnaya_derevnya.modules.fiscal.application.errors import OfdReceiptNotFound
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_receipt import (
    OfdReceiptStatus,
)
from myasnaya_derevnya.modules.fiscal.domain.permissions import (
    CASH_REGISTER_RECEIPT_MANAGE,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.base import (
    OfdReceiptRepository,
)
from myasnaya_derevnya.modules.inventory.presentation.inventory_api import (
    InventoryAPI,
    SaleLine,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PostOfdReceiptCommand:
    receipt_id: UUID


class PostOfdReceiptInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        receipt_repository: OfdReceiptRepository,
        inventory_api: InventoryAPI,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._receipt_repository = receipt_repository
        self._inventory_api = inventory_api
        self._transaction_manager = transaction_manager

    async def __call__(self, command: PostOfdReceiptCommand) -> OfdPostResult:
        user_id = await self._identity_provider.get_current_user_id()
        receipt = await self._receipt_repository.get_by_id(command.receipt_id)
        if receipt is None:
            raise OfdReceiptNotFound(command.receipt_id)

        await self._ensure_access(
            user_id=user_id, org_unit_id=receipt.org_unit_id
        )

        if receipt.status is OfdReceiptStatus.POSTED:
            return OfdPostResult(
                receipt_id=receipt.id, status=receipt.status.value
            )

        if await self._inventory_api.sale_posting_exists(receipt.id):
            receipt.mark_posted(posted_by=user_id)
            await self._receipt_repository.save(receipt)
            await self._transaction_manager.commit()
            return OfdPostResult(
                receipt_id=receipt.id, status=receipt.status.value
            )

        receipt.ensure_postable()

        try:
            await self._inventory_api.post_sale(
                document_id=receipt.id,
                org_unit_id=receipt.org_unit_id,
                occurred_at=receipt.doc_datetime,
                lines=[
                    SaleLine(
                        nomenclature_id=line.nomenclature_id,
                        quantity=line.quantity,
                    )
                    for line in receipt.lines
                    if line.nomenclature_id is not None
                ],
                posted_by=user_id,
            )
        except Exception as exc:
            await self._transaction_manager.rollback()

            # Проведение могло успеть записаться, а ответ — потеряться.
            if await self._inventory_api.sale_posting_exists(receipt.id):
                receipt.mark_posted(posted_by=user_id)
                await self._receipt_repository.save(receipt)
                await self._transaction_manager.commit()
                return OfdPostResult(
                    receipt_id=receipt.id, status=receipt.status.value
                )

            receipt.mark_failed(str(exc))
            await self._receipt_repository.save(receipt)
            await self._transaction_manager.commit()
            raise

        receipt.mark_posted(posted_by=user_id)
        await self._receipt_repository.save(receipt)
        await self._transaction_manager.commit()

        logger.info(
            "Чек ОФД проведён по складу",
            extra={
                "receipt_id": str(receipt.id),
                "reg_number": receipt.reg_number,
                "doc_number": receipt.doc_number,
                "org_unit_id": str(receipt.org_unit_id),
                "total_kopecks": receipt.total_kopecks,
            },
        )

        return OfdPostResult(receipt_id=receipt.id, status=receipt.status.value)

    async def _ensure_access(self, *, user_id: UUID, org_unit_id: UUID | None) -> None:
        if org_unit_id is not None:
            allowed = await self._staff_api.can(
                user_id=user_id,
                permission=CASH_REGISTER_RECEIPT_MANAGE,
                org_unit_id=org_unit_id,
            )
        else:
            allowed = await self._staff_api.can_anywhere(
                user_id=user_id, permission=CASH_REGISTER_RECEIPT_MANAGE
            )

        if not allowed:
            raise ForbiddenError()
