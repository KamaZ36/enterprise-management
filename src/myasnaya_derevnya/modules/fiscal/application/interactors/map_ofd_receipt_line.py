import logging
from dataclasses import dataclass
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.fiscal.application.dto import OfdLineMappingResult
from myasnaya_derevnya.modules.fiscal.application.errors import (
    NomenclatureForMappingNotFound,
    OfdReceiptLineNotFound,
)
from myasnaya_derevnya.modules.fiscal.domain.entities.ofd_product_alias import (
    OfdProductAlias,
)
from myasnaya_derevnya.modules.fiscal.domain.permissions import (
    CASH_REGISTER_RECEIPT_MANAGE,
)
from myasnaya_derevnya.modules.fiscal.infrastructure.repositories.ofd_receipt.base import (
    OfdReceiptRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MapOfdReceiptLineCommand:
    line_id: UUID
    nomenclature_id: UUID
    remember_barcode: bool = True


class MapOfdReceiptLineInteractor:
    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        catalog_api: CatalogAPI,
        receipt_repository: OfdReceiptRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._catalog_api = catalog_api
        self._receipt_repository = receipt_repository
        self._transaction_manager = transaction_manager

    async def __call__(self, command: MapOfdReceiptLineCommand) -> OfdLineMappingResult:
        user_id = await self._identity_provider.get_current_user_id()
        receipt = await self._find_receipt(command.line_id)
        await self._ensure_access(
            user_id=user_id, org_unit_id=receipt.org_unit_id
        )

        names = await self._catalog_api.nomenclature_names(
            {command.nomenclature_id}
        )
        if command.nomenclature_id not in names:
            raise NomenclatureForMappingNotFound(command.nomenclature_id)

        line = receipt.line(command.line_id)
        receipt.map_line(command.line_id, command.nomenclature_id)
        await self._receipt_repository.save_line(line)
        await self._receipt_repository.save(receipt)

        if command.remember_barcode and line.barcode is not None:
            await self._receipt_repository.save_alias(
                OfdProductAlias.create(
                    barcode=line.barcode,
                    nomenclature_id=command.nomenclature_id,
                    created_by=user_id,
                )
            )

        await self._transaction_manager.commit()

        logger.info(
            "Строка чека ОФД сопоставлена",
            extra={
                "receipt_id": str(receipt.id),
                "line_id": str(line.id),
                "nomenclature_id": str(command.nomenclature_id),
                "barcode": line.barcode,
            },
        )

        return OfdLineMappingResult(
            receipt_id=receipt.id,
            line_id=line.id,
            nomenclature_id=command.nomenclature_id,
            receipt_status=receipt.status.value,
        )

    async def _find_receipt(self, line_id: UUID):
        # Репозиторий ищет чек по строке: так HTTP-клиенту не нужно знать
        # идентификатор чека, чтобы сопоставить товар.
        receipt = await self._receipt_repository.get_by_line_id(line_id)
        if receipt is None:
            raise OfdReceiptLineNotFound(line_id)

        return receipt

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
