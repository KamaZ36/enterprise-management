import logging
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from myasnaya_derevnya.core.database.transaction_manager.base import TransactionManager
from myasnaya_derevnya.core.errors import ForbiddenError
from myasnaya_derevnya.core.identity_provider import IdentityProvider
from myasnaya_derevnya.modules.catalog.presentation.catalog_api import CatalogAPI
from myasnaya_derevnya.modules.pos.application.dto import PosProductMappingItem
from myasnaya_derevnya.modules.pos.application.errors import (
    NomenclatureForMappingNotFoundError,
    PosSourceNotFoundError,
)
from myasnaya_derevnya.modules.pos.domain.entities.product_mapping import (
    PosProductMapping,
)
from myasnaya_derevnya.modules.pos.domain.permissions import POS_RECEIPT_MANAGE
from myasnaya_derevnya.modules.pos.infrastructure.repositories.product_map.base import (
    PosProductMapRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.receipt.base import (
    PosReceiptRepository,
)
from myasnaya_derevnya.modules.pos.infrastructure.repositories.source.base import (
    PosSourceRepository,
)
from myasnaya_derevnya.modules.staff.presentation.staff_api import StaffAPI

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UpsertPosProductMappingCommand:
    source_id: UUID
    doka_product_guid: str
    nomenclature_id: UUID
    unit_factor: Decimal = Decimal(1)


class UpsertPosProductMappingInteractor:
    """Сопоставляет товар DoKa с номенклатурой и подтягивает уже принятые чеки."""

    def __init__(
        self,
        identity_provider: IdentityProvider,
        staff_api: StaffAPI,
        catalog_api: CatalogAPI,
        source_repository: PosSourceRepository,
        product_map_repository: PosProductMapRepository,
        receipt_repository: PosReceiptRepository,
        transaction_manager: TransactionManager,
    ) -> None:
        self._identity_provider = identity_provider
        self._staff_api = staff_api
        self._catalog_api = catalog_api
        self._source_repository = source_repository
        self._product_map_repository = product_map_repository
        self._receipt_repository = receipt_repository
        self._transaction_manager = transaction_manager

    async def __call__(
        self, command: UpsertPosProductMappingCommand
    ) -> PosProductMappingItem:
        user_id = await self._identity_provider.get_current_user_id()

        source = await self._source_repository.get_by_id(command.source_id)
        if source is None:
            raise PosSourceNotFoundError(command.source_id)

        allowed = await self._staff_api.can(
            user_id=user_id,
            permission=POS_RECEIPT_MANAGE,
            org_unit_id=source.org_unit_id,
        )
        if not allowed:
            raise ForbiddenError()

        names = await self._catalog_api.nomenclature_names(
            {command.nomenclature_id}
        )
        if command.nomenclature_id not in names:
            raise NomenclatureForMappingNotFoundError(command.nomenclature_id)

        mapping = PosProductMapping.create(
            source_id=source.id,
            doka_product_guid=command.doka_product_guid,
            nomenclature_id=command.nomenclature_id,
            unit_factor=command.unit_factor,
            created_by=user_id,
        )
        mapping_id = await self._product_map_repository.upsert(mapping)

        affected = await self._receipt_repository.apply_mapping(
            source_id=source.id,
            doka_product_guid=mapping.doka_product_guid,
            nomenclature_id=mapping.nomenclature_id,
            unit_factor=mapping.unit_factor,
        )
        await self._refresh_receipts(affected)
        await self._transaction_manager.commit()

        logger.info(
            "Товар DoKa сопоставлен с номенклатурой",
            extra={
                "source_id": str(source.id),
                "mapping_id": str(mapping_id),
                "doka_product_guid": mapping.doka_product_guid,
                "nomenclature_id": str(mapping.nomenclature_id),
                "unit_factor": str(mapping.unit_factor),
                "affected_receipts": len(affected),
            },
        )

        stored = await self._product_map_repository.get_by_id(mapping_id)

        return PosProductMappingItem(
            id=mapping_id,
            source_id=source.id,
            doka_product_guid=mapping.doka_product_guid,
            nomenclature_id=mapping.nomenclature_id,
            unit_factor=(
                stored.unit_factor if stored is not None else mapping.unit_factor
            ),
            is_active=stored.is_active if stored is not None else mapping.is_active,
            created_at=(
                stored.created_at if stored is not None else mapping.created_at
            ),
            updated_at=(
                stored.updated_at if stored is not None else mapping.updated_at
            ),
            nomenclature_name=names.get(mapping.nomenclature_id),
        )

    async def _refresh_receipts(self, receipt_ids: list[UUID]) -> None:
        for receipt_id in receipt_ids:
            receipt = await self._receipt_repository.get_by_id(receipt_id)
            if receipt is None:
                continue

            receipt.refresh_status()
            await self._receipt_repository.save(receipt)
